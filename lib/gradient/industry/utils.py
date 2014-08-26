import datetime
import logging
import urllib
import json
from xml.etree import ElementTree

from django.db import transaction
from django.db.models import Sum

from emtools.ccpeve.models import APIKey, apiroot

from gradient.index.models import Index
from gradient.uploader.models import MarketOrder as UploadedMarketOrder
from gradient.uploader.models import MarketOrderLastUpload

from gradient.dbutils import get_typename, get_stationsystem, get_systemregion
from gradient.dbutils import system_distance, get_itemname, get_membername

from gradient.industry.dbutils import InvType, get_decryptors

from gradient.industry.models import BlueprintOriginal
from gradient.industry.models import set_last_update
from gradient.industry.models import Transaction, TransactionInfo, Account
from gradient.industry.models import Journal, PriceList
from gradient.industry.models import MarketOrder, WantedMarketOrder
from gradient.industry.models import PublicMarketOrder, MarketPrice
from gradient.industry.models import Stock, StockLevel

SYNTH_BOOSTER_BPC = [
    "Synth Blue Pill Booster Blueprint",
    "Synth Crash Booster Blueprint",
    "Synth Drop Booster Blueprint",
    "Synth Exile Booster Blueprint",
    "Synth Frentix Booster Blueprint",
    "Synth Mindflood Booster Blueprint",
    "Synth Sooth Sayer Booster Blueprint",
    "Synth X-Instinct Booster Blueprint",
    ]

# We use Jita prices for these for the cost calculation (as per
# Damian)
USE_JITA_INDEX = [
    "Amber Mykoserocin",
    "Azure Mykoserocin",
    "Celadon Mykoserocin",
    "Golden Mykoserocin",
    "Lime Mykoserocin",
    "Malachite Mykoserocin",
    "Vermillion Mykoserocin",
    "Viridian Mykoserocin",
    ]

ENCRYPTION_SKILL = 4
SCIENCE1_SKILL = 4
SCIENCE2_SKILL = 4
META_LEVEL = 0

def blueprints(invtype):
    """
    Return a list of Blueprint objects which can be used to produce
    this typename.
    """
    bptype = invtype.blueprint()
    # No blueprints
    if bptype is None:
        return []
    # See if we have the BPO
    try:
        bpo = BlueprintOriginal.objects.get(typename=bptype.typename)
        return [Blueprint(bptype, me=bpo.me, pe=bpo.pe, source='Owned BPO')]
    except BlueprintOriginal.DoesNotExist:
        pass
    # Nope. Can we invent this blueprint?
    t1bp = bptype.invented_from()
    if t1bp is not None:
        try:
            bpo = BlueprintOriginal.objects.get(typename=t1bp.typename)
            return invented_blueprints(bptype)
        except BlueprintOriginal.DoesNotExist:
            pass
    # Maybe we regularly by the BPCs?
    if bptype.typename in SYNTH_BOOSTER_BPC:
        return [Blueprint(bptype, me=0, pe=0, source='Market')]
    # FIXME!
    # - Reverse engineering
    return []

def invented_blueprints(t2bp):
    """
    Return a list of blueprint objects for a blueprint name.
    """
    t2product = t2bp.product()
    t1product = t2product.metatype_parent()
    t1group = t1product.group()
    t1bp = t1product.blueprint()

    base_extra = Bag()
    for reqtype, qty, dpj, recycle in t1bp.typerequirements('Invention'):
        if reqtype.group() == 'Data Interfaces':
            continue
        if dpj > 0:
            base_extra.add(reqtype.typename, qty * dpj)

    if (t1group in ('Battlecruiser', 'Battleship') or
        t2product.typename == 'Hulk'):
        basechance = 0.2
    elif (t1group in ('Cruiser', 'Industrial') or
          t2product.typename == 'Mackinaw'):
        basechance = 0.25
    elif (t1group in ('Frigate', 'Destroyer', 'Freighter') or
          t2product.typename == 'Skiff'):
        basechance = 0.3
    else:
        basechance = 0.4
    t2maxruns = t2bp.maxproductionlimit()
    blueprints = []
    for decryptor in get_decryptors(t1product.race()):
        chance = (basechance *
                  ((1 + 0.01 * ENCRYPTION_SKILL) *
                   (1 + ((0.02 * (SCIENCE1_SKILL + SCIENCE2_SKILL)) *
                         (5.0 / (5 - META_LEVEL)))) *
                   decryptor.chance))
        runs = min(max(int((t2maxruns / 10.0) +
                           decryptor.runs),
                       1),
                   t2maxruns)
        me = -4 + decryptor.me
        pe = -4 + decryptor.pe
        extra = base_extra.copy()
        if decryptor.typename:
            extra[decryptor.typename] = 1
        blueprints.append(Blueprint(t2bp,
                                    me=me, pe=pe,
                                    runs=runs,
                                    source='Invention',
                                    extra=extra * (1.0/(chance*runs))))
    return blueprints


def build(blueprint):
    """
    Return the materials needed to build this blueprint.

    Excluding blueprint.extra.
    """
    bptype = blueprint.invtype
    product = bptype.product()
    base = Bag()
    for reqtype, qty in product.typematerials():
        base[reqtype.typename] = qty
    more = Bag()
    for reqtype, qty, dpj, recycle in bptype.typerequirements('Manufacturing'):
        if dpj < 0.00001:
            continue
        if recycle > 0:
            for reqtype2, qty2 in reqtype.typematerials():
                if qty2 > base[reqtype2.typename]:
                    del base[reqtype2.typename]
                else:
                    base[reqtype2.typename] -= qty2
        if dpj > 0.99999:
            more[reqtype.typename] = qty
        else:
            more[reqtype.typename] = qty * dpj
    bwf = bptype.wastefactor()
    if blueprint.me >= 0:
        wf = bwf * 0.01 * (1.0 / (blueprint.me + 1))
    else:
        wf = bwf * 0.01 * (1 + 0.1 - blueprint.me * 0.1)
    for (key, val) in base.items():
        base[key] += int(round(val * wf))
    return (base + more)

class Blueprint(object):
    def __init__(self, invtype, me=0, pe=0, runs=1,
                 source=None, extra=None):
        self.invtype = invtype
        self.me = me
        self.pe = pe
        self.runs = runs
        self.source = source
        if extra is None:
            self.extra = Bag()
        else:
            self.extra = extra

    def __repr__(self):
        return ("<Blueprint %s from %s, ME %s, PE %s, %s extra>" %
                (self.invtype.typename, self.source, self.me, self.pe,
                 len(self.extra)))

class Bag(object):
    def __init__(self, initial={}):
        self.contents = {}
        self.contents.update(initial)

    def __repr__(self):
        return "<Bag %s>" % ", ".join(["%s=%r" % (k, v) for (k, v) in
                                       sorted(self.contents.items())])

    def __iter__(self):
        for k, v in self.contents.items():
            if v != 0:
                yield k

    def items(self):
        return [(k, v) for (k, v) in self.contents.items()
                if v != 0]

    def copy(self):
        result = self.__class__()
        result.contents.update(self.contents)
        return result

    def add(self, name, qty):
        self.contents.setdefault(name, 0)
        self.contents[name] += qty

    def __len__(self):
        return len(self.contents)

    def __getitem__(self, k):
        return self.contents.get(k, 0)

    def __setitem__(self, k, v):
        self.contents[k] = v

    def __delitem__(self, k):
        if k in self.contents:
            del self.contents[k]

    def __add__(self, other):
        result = self.copy()
        for k, v in other.items():
            result.add(k, v)
        return result

    def __iadd__(self, other):
        for k, v in other.items():
            self.add(k, v)
        return self

    def __sub__(self, other):
        result = self.copy()
        for k, v in other.items():
            result.add(k, -v)
        return result

    def __isub__(self, other):
        for k, v in other.items():
            self.add(k, -v)
        return self

    def __mul__(self, number):
        result = self.copy()
        result *= number
        return result

    def __imul__(self, number):
        for k in self:
            self[k] *= number
        return self

class IndexCalculator(object):
    def __init__(self):
        self.index = {}

        for row in Index.objects.all():
            if row.typename in USE_JITA_INDEX:
                self.index[row.typename] = row.jita
            else:
                self.index[row.typename] = row.republic

    def bag_cost(self, bag):
        total = 0.0
        for typename, quantity in bag.items():
            value = self.index.get(typename)
            if value is None:
                value = self.cost(typename)
            if value is None:
                value = 0.0
            total += value * quantity
        return total

    def materialcost(self, typename):
        if typename in self.index:
            return self.index[typename]
        else:
            return None

    def cost(self, typename):
        """
        Return the cost of this typename.
        """
        invtype = InvType.from_typename(typename)
        val = (self.cost_blueprint(invtype) or
               self.cost_reaction(invtype) or
               self.cost_lpstore(invtype) or
               self.cost_purchase(invtype))
        return val

    def cost_blueprint(self, invtype):
        bplist = blueprints(invtype)
        if len(bplist) == 0:
            return None
        else:
            bp = bplist[0]
            return (self.bag_cost(bp.extra) +
                    self.bag_cost(build(bp))) / float(invtype.portionsize())

    def cost_reaction(self, invtype):
        bag = self.reaction_bag(invtype)
        if bag is None:
            return None
        return self.bag_cost(bag)

    def reaction_bag(self, invtype):
        result_runs = invtype.attribute('moonMiningAmount')
        output_qty, inputs = invtype.reacted_from()
        if inputs is None:
            return None
        bag = Bag()
        for reqtype, reqqty in inputs:
            bag[reqtype.typename] += (reqqty *
                                      reqtype.attribute('moonMiningAmount'))
        # Also add half a control tower worth of fuel ...
        tower = InvType.from_typename('Minmatar Control Tower')
        for (resourcetype,
             quantity,
             minsecuritylevel,
             factionid) in (tower.controltowerresources('Online') +
                            tower.controltowerresources('Power') +
                            tower.controltowerresources('CPU')):
             if minsecuritylevel is not None:
                 continue
             bag[resourcetype.typename] = quantity * 0.5
        bag *= 1.0 / (output_qty * result_runs)
        return bag

    def cost_lpstore(self, invtype):
        # FIXME!
        return None

    def cost_purchase(self, invtype):
        price = get_transaction_price('buy', invtype.typeid, 7)
        if price == 0.0:
            price = get_transaction_price('buy', invtype.typeid, 28)
        if price == 0.0:
            return None
        else:
            return price

    def get_bag_materials(self, bag):
        mats = []
        for typename, qty in bag.items():
            type_cost = self.materialcost(typename)
            if type_cost is None:
                type_cost = self.cost(typename)
            if type_cost is None:
                type_cost = 0.0
            price_pu = type_cost
            price_total = price_pu * qty
            mats.append((typename, qty, price_pu, price_total))
        return mats


def get_component_list(typename):
    mfglinecosts = get_mfglinecosts()
    invtype = InvType.from_typename(typename)
    # Blueprint
    bplist = blueprints(invtype)
    index = IndexCalculator()
    if len(bplist) > 0:
        result = []
        for bp in bplist:
            c = Component()
            c.safetymargin = get_safetymargin(invtype, mfglinecosts)
            c.portionsize = invtype.portionsize()
            mats1 = index.get_bag_materials(bp.extra)
            c.add_section('Blueprint', sorted(mats1))
            mats2 = index.get_bag_materials(build(bp))
            c.add_section('Materials', sorted(mats2))
            c.total = sum(price_total
                          for (typename, qty, price_pu, price_total)
                          in mats1 + mats2
                          ) * c.safetymargin * 1.0/c.portionsize
            result.append(c)
        return result
    # Reaction
    result_runs = invtype.attribute('moonMiningAmount')
    output_qty, inputs = invtype.reacted_from()
    if inputs is not None:
        c = Component()
        c.portionsize = int(output_qty * result_runs)
        bag = Bag()
        for reqtype, reqqty in inputs:
            bag[reqtype.typename] += (reqqty *
                                      reqtype.attribute('moonMiningAmount'))
        mats1 = index.get_bag_materials(bag)
        c.add_section('Reaction', sorted(mats1))
        # Also add half a control tower worth of fuel ...
        bag = Bag()
        tower = InvType.from_typename('Minmatar Control Tower')
        for (resourcetype,
             quantity,
             minsecuritylevel,
             factionid) in (tower.controltowerresources('Online') +
                            tower.controltowerresources('Power') +
                            tower.controltowerresources('CPU')):
             if minsecuritylevel is not None:
                 continue
             bag[resourcetype.typename] = quantity * 0.5
        mats2 = index.get_bag_materials(bag)
        c.add_section('Tower Fuel (Half a Minmatar Large)', sorted(mats2))
        c.total = sum(price_total
                      for (typename, qty, price_pu, price_total)
                      in mats1 + mats2
                      ) / float(c.portionsize)
        return [c]
    # Index
    price = index.materialcost(invtype.typename)
    if price is not None:
        c = Component()
        c.add_section('Material Index',
                      [(invtype.typename, 1, price, price)])
        c.total = price
        return [c]
    # Purchase
    price = index.cost_purchase(invtype)
    if price is not None:
        c = Component()
        c.add_section('Market Purchase',
                      [(invtype.typename, 1, price, price)])
        c.total = price
        return [c]

class Component(object):
    def __init__(self):
        self.sections = []
        self.total = 0.0
        self.portionsize = 1
        self.safetymargin = 1.0

    def add_section(self, name, entries):
        self.sections.append((name, entries))


# model update
def update():
    log = logging.getLogger('industry')
    log.info("Running industry update")
    transaction.commit_unless_managed()
    transaction.enter_transaction_management()
    transaction.managed(True)
    grd = APIKey.objects.get(name='Gradient').corp()
    log.info("Update public market")
    update_publicmarket()
    transaction.commit()
    log.info("Update market prices")
    update_marketprice()
    transaction.commit()
    log.info("Update transactions and journal")
    for accountkey in [1000, 1001, 1002, 1003, 1004, 1005, 1006]:
        try:
            update_transaction(grd, accountkey)
        except:
            logging.exception("Error during update_transaction")
        try:
            update_journal(grd, accountkey)
        except:
            logging.exception("Error during update_journal")
    transaction.commit()
    log.info("Update transaction info")
    add_transaction_info(grd)
    transaction.commit()
    log.info("Update price list")
    update_pricelist(grd)
    transaction.commit()
    log.info("Update corp market orders")
    update_marketorder(grd)
    transaction.commit()
    log.info("Update stock levels")
    update_stock(grd)
    transaction.commit()
    log.info("Industry update done")
    transaction.leave_transaction_management()

MOLDENHEATH = 10000028
HEIMATAR = 10000030
METROPOLIS = 10000042
THEFORGE = 10000002
RENS = 30002510
RENS_BTT = 60004588
JITA44 = 60003760

def update_publicmarket():
    log = logging.getLogger('industry')
    for pl in PriceList.objects.all():
        for regionid in [HEIMATAR, METROPOLIS, MOLDENHEATH, THEFORGE]:
            query = urllib.urlencode([('regionlimit', regionid),
                                      ('typeid', str(pl.typeid))])
            url = "http://api.eve-central.com/api/quicklook?" + query
            try:
                data = urllib.urlopen(url).read()
                tree = ElementTree.fromstring(data)
            except Exception as e:
                log.info("Couldn't retrieve public market info for %s: %s" %
                         (pl.typename, str(e)))
            else:
                publicmarket_save(regionid, pl.typeid, tree)
    set_last_update('public-market', datetime.datetime.utcnow())

def publicmarket_save(regionid, typeid, tree):
    now = datetime.datetime.utcnow()
    reported_time = tree.find("quicklook//reported_time")
    if reported_time is None:
        evemetrics_time = datetime.datetime(2000, 1, 1)
    else:
        # For a reason completely beyond me, evecental does not report
        # years. Add the year to the time stamp to avoid a silly Feb
        # 29 bug.
        evemetrics_time = datetime.datetime.strptime(
            "%s-%s" % (now.year, reported_time.text.strip()),
            "%Y-%m-%d %H:%M:%S"
            )
    try:
        gdu_time = MarketOrderLastUpload.objects.get(regionid=regionid,
                                                     typeid=typeid
                                                     ).cachetimestamp
    except MarketOrderLastUpload.DoesNotExist:
        gdu_time = datetime.datetime(2000, 1, 1)
    # This can break when the date changes from one year to the next.
    # We'll have to live with that.
    if evemetrics_time > gdu_time:
        publicmarket_save2(regionid, typeid, tree)
    else:
        PublicMarketOrder.objects.filter(regionid=regionid,
                                         typeid=typeid).delete()
        for mo in UploadedMarketOrder.objects.filter(regionid=regionid,
                                                     typeid=typeid):
            PublicMarketOrder.objects.create(
                last_seen=now,
                ordertype="buy" if mo.bid else "sell",
                regionid=mo.regionid,
                systemid=mo.solarsystemid,
                stationid=mo.stationid,
                range=mo.range,
                typeid=mo.typeid,
                volremain=mo.volremaining,
                price=mo.price
                )

def publicmarket_save2(regionid, typeid, tree):
    now = datetime.datetime.utcnow()
    assert str(typeid) == tree.find("quicklook/item").text.strip()
    PublicMarketOrder.objects.filter(regionid=regionid, typeid=typeid).delete()
    def save_order(ordertype, order):
        stationid = int(order.find("station").text)
        PublicMarketOrder.objects.create(
            last_seen=now,
            ordertype=ordertype,
            regionid=int(order.find("region").text),
            systemid=get_stationsystem(stationid),
            stationid=stationid,
            range=int(order.find("range").text),
            typeid=typeid,
            volremain=int(order.find("vol_remain").text),
            price = float(order.find("price").text)
            )
    for order in tree.findall("quicklook/sell_orders/order"):
        save_order('sell', order)
    for order in tree.findall("quicklook/buy_orders/order"):
        save_order('buy', order)

def update_marketprice():
    typeid_set = set()
    orders = {}
    totalvolume = {}
    btt_orders = {}
    btt_totalvolume = {}
    for pmo in PublicMarketOrder.objects.filter(ordertype='sell',
                                                regionid=HEIMATAR):
        typeid_set.add(pmo.typeid)
        orders.setdefault(pmo.typeid, [])
        orders[pmo.typeid].append((pmo.price, pmo.volremain, pmo.last_seen))
        totalvolume.setdefault(pmo.typeid, 0)
        totalvolume[pmo.typeid] += pmo.volremain
        if pmo.stationid == RENS_BTT:
            btt_orders.setdefault(pmo.typeid, [])
            btt_orders[pmo.typeid].append((pmo.price, pmo.volremain,
                                           pmo.last_seen))
            btt_totalvolume.setdefault(pmo.typeid, 0)
            btt_totalvolume[pmo.typeid] += pmo.volremain

    MarketPrice.objects.all().delete()
    for typeid in typeid_set:
        if typeid in btt_orders:
            typeorders = btt_orders[typeid]
            cutoff = btt_totalvolume[typeid] * 0.05
        else:
            typeorders = orders[typeid]
            cutoff = totalvolume[typeid] * 0.05
        typeorders.sort()
        volumesum = 0
        for price, volume, last_seen in typeorders:
            volumesum += volume
            if volumesum > cutoff:
                MarketPrice.objects.create(last_seen=last_seen,
                                           typeid=typeid,
                                           price=price)
                break

ROWS = 2560

def update_transaction(grd, accountkey):
    def save_entry(entry):
        try:
            Transaction.objects.get(transactionid=entry.transactionID)
            return
        except Transaction.DoesNotExist:
            pass
        Transaction.objects.create(
            transactionid=entry.transactionID,
            accountkey=accountkey,
            timestamp=datetime.datetime.utcfromtimestamp(entry.transactionDateTime),
            typeid=entry.typeID,
            quantity=entry.quantity,
            price=entry.price,
            clientid=entry.clientID,
            characterid=entry.characterID,
            stationid=entry.stationID,
            transactiontype=entry.transactionType,
            journalid=entry.journalTransactionID
            )
    gwt = grd.WalletTransactions(rowCount=ROWS, accountKey=accountkey)
    set_last_update('transactions',
                    datetime.datetime.utcfromtimestamp(gwt._meta.currentTime))
    for entry in gwt.transactions:
        save_entry(entry)
    while len(gwt.transactions) >= ROWS:
        fromid = min(entry.transactionID for entry in gwt.transactions)
        gwt = grd.WalletTransactions(fromID=fromid,
                                     rowCount=ROWS,
                                     accountKey=accountkey)
        for entry in gwt.transactions:
            save_entry(entry)

def add_transaction_info(grd):
    api = apiroot()
    standingmap = dict((row.contactID, row.standing)
                       for row in grd.ContactList().allianceContactList)
    for entry in Transaction.objects.filter(info=None):
        info = TransactionInfo()
        info.transaction = entry
        info.account = Account.objects.get(accountkey=entry.accountkey)
        info.typename = get_typename(entry.typeid)
        if info.typename is None:
            continue
        try:
            pl = PriceList.objects.get(typeid=entry.typeid)
            info.cost = pl.productioncost
            info.safetymargin = pl.safetymargin
        except PriceList.DoesNotExist:
            try:
                index = Index.objects.filter(typeid=entry.typeid)[0:1].get()
                info.cost = index.republic
                info.safetymargin = 1.0
            except Index.DoesNotExist:
                info.cost = 0.0
                info.safetymargin = 1.1
        info.stationname = get_itemname(entry.stationid)
        if entry.characterid is not None:
            info.charactername = get_membername(entry.characterid)
        try:
            charinfo = api.eve.CharacterInfo(characterID=entry.clientid)
        except:
            pass
        else:
            info.clientname = charinfo.characterName
            info.clientstanding = standingmap.get(charinfo.characterID, None)
            info.clientcorp = charinfo.corporation
            info.clientcorpid = charinfo.corporationID
            info.clientcorpstanding = standingmap.get(charinfo.corporationID,
                                                      None)
            if hasattr(charinfo, 'allianceID'):
                info.clientalliance = charinfo.alliance
                info.clientallianceid = charinfo.allianceID
                info.clientalliancestanding = standingmap.get(
                    charinfo.allianceID,
                    None)
            info.save()
            transaction.commit()
            continue
        # It's a CorporationID!
        info.clientname = None
        info.clientstanding = None
        info.clientcorpid = entry.clientid
        name = get_itemname(entry.clientid)
        if name is not None: # NPC corp
            info.clientcorp = name
            info.clientcorpstanding = standingmap.get(entry.clientid, None)
            info.save()
            transaction.commit()
            continue
        # Player corp
        try:
            corpinfo = api.eve.CorporationSheet(corporationID=entry.clientid)
        except: # Something bad happened, ignore this
            transaction.rollback()
            continue
        info.clientcorp = corpinfo.corporationName
        info.clientcorpstanding = standingmap.get(corpinfo.corporationID,
                                                  None)
        if hasattr(corpinfo, 'allianceID'):
            info.clientalliance = corpinfo.allianceName
            info.clientallianceid = corpinfo.allianceID
            info.clientalliancestanding = standingmap.get(corpinfo.allianceID,
                                                          None)
        info.save()
        transaction.commit()

def update_journal(grd, accountkey):
    def save_entry(entry):
        try:
            Journal.objects.get(journalid=entry.refID)
            return
        except Journal.DoesNotExist:
            pass
        Journal.objects.create(
            journalid=entry.refID,
            accountkey=accountkey,
            timestamp=datetime.datetime.utcfromtimestamp(entry.date),
            reftypeid=entry.refTypeID,
            amount=entry.amount,
            ownerid1=entry.ownerID1,
            ownerid2=entry.ownerID2,
            argname1=entry.argName1,
            argid1=entry.argID1,
            reason=entry.reason
            )
    gwj = grd.WalletJournal(rowCount=ROWS, accountKey=accountkey)
    set_last_update('journal',
                    datetime.datetime.utcfromtimestamp(gwj._meta.currentTime))
    for entry in gwj.entries:
        save_entry(entry)
    while len(gwj.entries) >= ROWS:
        fromid = min(entry.refID for entry in gwj.entries)
        gwj = grd.WalletJournal(fromID=fromid,
                                rowCount=ROWS,
                                accountKey=accountkey)
        for entry in gwj.entries:
            save_entry(entry)

def update_pricelist(grd):
    set_last_update('pricelist', datetime.datetime.utcnow())
    index = IndexCalculator()
    bposet = set()
    inventable = []
    known = set()
    PriceList.objects.all().delete()
    mfglinecosts = get_mfglinecosts()
    for bpo in BlueprintOriginal.objects.all():
        bposet.add(bpo.typeid)
        bptype = InvType(bpo.typeid, bpo.typename)
        product = bptype.product()
        if product is None:
            raise RuntimeError("Can't find product for BPO %s (%s)"
                               % (bpo.typeid, bpo.typename))
        productioncost = index.cost(product.typename)
        if productioncost is None or not productioncost > 0:
            continue
        safetymargin = get_safetymargin(product, mfglinecosts)
        PriceList.objects.create(typename=product.typename,
                                 typeid=product.typeid,
                                 productioncost=productioncost,
                                 safetymargin=safetymargin)
        known.add(product.typeid)
        # We lack the parts for the Anshar...
        if not (product.typename == 'Obelisk' or
                product.group().startswith("Rig ")):
            inventable.extend(bptype.invent_to())

    for bpc in inventable:
        if bpc.typeid in bposet:
            continue
        product = bpc.product()
        productioncost = index.cost(product.typename)
        if productioncost is None or not productioncost > 0:
            continue
        safetymargin = get_safetymargin(product, mfglinecosts)
        PriceList.objects.create(typename=product.typename,
                                 typeid=product.typeid,
                                 productioncost=productioncost,
                                 safetymargin=safetymargin)
        known.add(product.typeid)
    for wmo in WantedMarketOrder.objects.filter(forcorp=True):
        if wmo.typeid in known:
            continue
        typename = get_typename(wmo.typeid)
        typeid = wmo.typeid
        product = InvType(typeid, typename)
        productioncost = index.cost(typename)
        if productioncost is None or not productioncost > 0:
            continue
        safetymargin = 1.02 # Broker's fee of 1%
        PriceList.objects.create(typename=typename,
                                 typeid=typeid,
                                 productioncost=productioncost,
                                 safetymargin=safetymargin)
        known.add(typeid)
    for bpname in SYNTH_BOOSTER_BPC:
        bptype = InvType.from_typename(bpname)
        product = bptype.product()
        if product.typeid in known:
            continue
        productioncost = index.cost(product.typename)
        if productioncost is None or not productioncost > 0:
            continue
        productioncost += 25000 # Per-run BPC cost as per Damian
        PriceList.objects.create(typename=product.typename,
                                 typeid=product.typeid,
                                 productioncost=productioncost,
                                 safetymargin=1.0)
        known.add(product.typeid)

def get_mfglinecosts():
    # In some cases querying the manufacturing line cost from the API
    # could expose sensitive intel so we'll hard-code some costs
    # for now and monitor over time. For non-sensitive locations we get
    # the actual cost index from the API (defaulting to 5%).
    systems_url = "http://public-crest.eveonline.com/industry/systems/"
    system_costs = json.loads(urllib.urlopen(system_url).read())
    normal_cost_index = 0.05
    for system in system_costs['items']:
        if system['solarSystem']['id'] == 30002544:
            for index in system['systemCostIndices']:
                if index['activityName'] == "Manufacturing":
                    normal_cost_index = index['costIndex']
    return {
        'normal': 1.10 + normal_cost_index,
        'capitals': 1.12,
        'tech3': 1.05
        }

def get_safetymargin(product, mfglinecosts):
    # We allocate a "safety margin" for some items we manufacture,
    # the specific values were recommended by Theron. At some point
    # we should probably make this data-driven with a UI for Gradient
    # admins to tweak it, but it's been fine for years. On top of that,
    # the Crius expansion adds non-trivial fees for manufacturing lines.
    # These vary by the location of the manufacturing line, which for
    # Gradient varies by what is being manufactured.
    tl = int(product.attribute("techLevel") or 1.0)
    if tl == 1:
        group = product.group()
        if group in ['Carrier']:
            return 1.2 * mfglinecosts['capitals']
        elif group in ['Dreadnought']:
            return 1.1 * mfglinecosts['capitals']
        elif group in ['Industrial Command Ship',
                       'Capital Industrial Ship']:
            return 1.11 * mfglinecosts['capitals']
        else:
            return 1.0 * mfglinecosts['normal']
    elif tl == 2:
        category = product.category()
        if category == 'Charge':
            return 1.5 * mfglinecosts['normal']
        elif product.typename in ['Covert Ops Cloaking Device II',
                                  'Improved Cloaking Device II']:
            return 2.5 * mfglinecosts['normal']
        else:
            return 1.2 * mfglinecosts['normal']
    elif tl == 3:
        return 1.15 * mfglinecosts['tech3']
    else:
        raise RuntimeError('Unknown tech level %s (%s)' %
                           (tl, product.typename))

def update_marketorder(grd):
    index = IndexCalculator()
    pricelist = dict((p.typename, p.productioncost * p.safetymargin)
                     for p in PriceList.objects.all())
    MarketOrder.objects.all().delete()
    gmo = grd.MarketOrders()
    have_orders = set()
    wanted_orders = {}
    for wmo in WantedMarketOrder.objects.all():
        wanted_orders.setdefault((wmo.characterid, wmo.stationid,
                                  wmo.ordertype), set())
        wanted_orders[(wmo.characterid, wmo.stationid,
                       wmo.ordertype)].add(wmo.typeid)
    set_last_update('marketorders',
                    datetime.datetime.utcfromtimestamp(gmo._meta.currentTime))
    for order in gmo.orders:
        ordertype = 'buy' if order.bid else 'sell'
        expires = (datetime.datetime.utcfromtimestamp(order.issued) +
                   datetime.timedelta(days=order.duration))
        volremaining = order.volRemaining
        if order.orderState != 0:
            volremaining = 0
            expires = datetime.datetime.utcnow()
            if (order.charID, order.stationID,
                ordertype, order.typeID) in have_orders:
                continue
            if order.typeID not in wanted_orders.get((order.charID,
                                                      order.stationID,
                                                      ordertype),
                                                     set()):
                continue
        have_orders.add((order.charID, order.stationID,
                         ordertype, order.typeID))
        typename = get_typename(order.typeID)
        if typename is None:
            typename = '<typeID %s>' % order.typeID
        productioncost = pricelist.get(typename)
        if productioncost is None:
            productioncost = index.materialcost(typename)
        if productioncost is None:
            productioncost = 0.0
        sales7d = get_transactions(ordertype, order.stationID,
                                   order.typeID, 7) / 7.0
        sales28d = get_transactions(ordertype, order.stationID,
                                    order.typeID, 28) / 28.0
        if sales7d > 0:
            salesperday = sales7d
        else:
            salesperday = sales28d
        competitionprice = get_competitionprice(
            ordertype,
            order.stationID,
            order.typeID,
            volremaining,
            order.price,
            order.range
            )
        if sales28d == 0 and sales7d == 0:
            trend = 0.0
        else:
            trend = sales7d / float(sales7d + sales28d)
        MarketOrder.objects.create(
            characterid=order.charID,
            stationid=order.stationID,
            typeid=order.typeID,
            ordertype=ordertype,
            expires=expires,
            volremaining=volremaining,
            price=order.price,
            productioncost=productioncost,
            salesperday=salesperday,
            competitionprice=competitionprice,
            trend=trend)

def get_transactions(ordertype, stationid, typeid, days):
    ts = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    sales = Transaction.objects.filter(
        timestamp__gte=ts,
        typeid=typeid,
        stationid=stationid,
        transactiontype=ordertype
        ).aggregate(
        Sum('quantity')
        )['quantity__sum']
    if sales is None:
        return 0
    else:
        return sales

def get_transaction_price(ordertype, typeid, days):
    ts = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    qty = 0
    cost = 0
    for tr in Transaction.objects.filter(timestamp__gte=ts,
                                         typeid=typeid,
                                         transactiontype=ordertype
                                         ):
        qty += tr.quantity
        cost += tr.price * tr.quantity
    if qty == 0:
        return 0.0
    else:
        return cost / qty

def last_price(ordertype, stationid, typeid):
    try:
        t = Transaction.objects.filter(
            typeid=typeid, stationid=stationid, transactiontype=ordertype
            )[0:1].get()
        return t.price
    except Transaction.DoesNotExist:
        return 0.0

# - High Sec (Hangar, 4)
# - Restricted (CorpSAG2, 116)
# - Production (CorpSAG3, 117)
# - Incoming (CorpSAG4, 118)
# - Corp Ops (CorpSAG5, 119)
# - Equipment (CorpSAG6, 120)
# - Outgoing (CorpSAG7, 121)
# - Deliveries (CorpMarket, 62)
STOCK_FLAGS = set([4, 62, 116, 117, 118])
HANGAR_OUTGOING = 121
# In case we ever need the itemIDs:
# 1490307531 - Sell for corp
# 1872977592 - Synth Booster
# 1883454961 - T3 Stuff
# 1490307531 - To Bosboger
# 1001404934572 - To Dal
# 1004052383695 - To Jav
# 713610744 - To Research
CAN_TYPEIDS = set([3713, 17366, 17367])
# We also only care about the first level unless it's an office (typeID 27)
OFFICE_TYPEID = 27
def update_stock(grd):
    stocks = {}
    gal = grd.AssetList()
    set_last_update('stocks',
                    datetime.datetime.utcfromtimestamp(gal._meta.currentTime))
    for asset in gal.assets:
        stationid = make_stationid(asset.locationID)
        if stationid is None: # in space
            continue
        if asset.flag in STOCK_FLAGS:
            stocks.setdefault(stationid, Bag())
            stocks[stationid][asset.typeID] += asset.quantity
        if asset.typeID == OFFICE_TYPEID and hasattr(asset, 'contents'):
            for asset2 in asset.contents:
                if asset2.flag in STOCK_FLAGS:
                    stocks.setdefault(stationid, Bag())
                    stocks[stationid][asset2.typeID] += asset2.quantity

                if (asset2.flag == HANGAR_OUTGOING and
                    asset2.typeID in CAN_TYPEIDS
                    and hasattr(asset2, 'contents')): # Outgoing
                    for asset3 in asset2.contents:
                        stocks.setdefault(stationid, Bag())
                        stocks[stationid][asset3.typeID] += asset3.quantity
    Stock.objects.all().delete()
    for stationid, levels in stocks.items():
        for typeid, quantity in levels.items():
            typename = get_typename(typeid)
            if typename is None:
                typename = '<TypeID %s>' % typeid
            try:
                pl = PriceList.objects.get(typeid=typeid)
            except PriceList.DoesNotExist:
                pl = None
            try:
                sl = StockLevel.objects.get(typeid=typeid,
                                            stationid=stationid)
            except StockLevel.DoesNotExist:
                sl = None
            Stock.objects.create(typename=typename,
                                 typeid=typeid,
                                 stationid=stationid,
                                 current=quantity,
                                 price=pl,
                                 level=sl)

def make_stationid(locationid):
    if 61000000 <= locationid < 64000000: # Station ID
        return locationid
    elif 66000000 <= locationid < 67000000: # Office in normal station
        return locationid - 6000001
    elif 67000000 <= locationid < 68000000: # Office in outpost
        return locationid - 6000000
    else:
        return None

def get_competitionprice(ordertype, stationid, typeid, volremaining,
                         orderprice, orderrange):
    systemid = get_stationsystem(stationid)
    regionid = get_systemregion(systemid)
    qs = PublicMarketOrder.objects.filter(
        ordertype=ordertype,
        regionid=regionid,
        typeid=typeid,
        volremain__gt=volremaining * 0.05)
    price = None
    for pmo in qs:
        if pmo.stationid == stationid and abs(pmo.price - orderprice) < 0.005:
            continue
        if ordertype == 'sell':
            max_distance = 3
        else:
            max_distance = pmo.range + orderrange
        if system_distance(pmo.systemid, systemid) <= max_distance:
            if price is None:
                price = pmo.price
            else:
                price = min(price, pmo.price)
    return price


def redo_cache():
    """
    The models cache quite a few names for ids to make display faster.
    Rebuild all of those.
    """
    for obj in BlueprintOriginal.objects.all():
        obj.typename = get_typename(obj.typeid)
        if obj.typename is None:
            print "Bad typeID in BlueprintOriginal: %s" % obj.typeid
        else:
            obj.save()
    for obj in TransactionInfo.objects.all():
        obj.typename = get_typename(obj.transaction.typeid)
        if obj.typename is None:
            print "Bad typeID in TransactionInfo: %s" % obj.typeid
        else:
            obj.save()
    for obj in PriceList.objects.all():
        obj.typename = get_typename(obj.typeid)
        if obj.typename is None:
            print "Bad typeID in PriceList: %s" % obj.typeid
        else:
            obj.save()
    for obj in WantedMarketOrder.objects.all():
        obj.typename = get_typename(obj.typeid)
        if obj.typename is None:
            print "Bad typeID in WantedMarketOrder: %s" % obj.typeid
        else:
            obj.save()
    for obj in StockLevel.objects.all():
        obj.typename = get_typename(obj.typeid)
        if obj.typename is None:
            print "Bad typeID in StockLevel: %s" % obj.typeid
        else:
            obj.save()
    for obj in Stock.objects.all():
        obj.typename = get_typename(obj.typeid)
        if obj.typename is None:
            print "Bad typeID in Stock: %s" % obj.typeid
        else:
            obj.save()
