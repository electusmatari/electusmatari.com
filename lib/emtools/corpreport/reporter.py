from django.db import connection

from emtools.ccpeve.models import Balance, Asset, Division, IndustryJob
from emtools.ccpeve.models import MarketOrder
from emtools.ccpeve.models import Type, InvItem, Station, SolarSystem, Flag
from emtools.industry.build import cost
from emtools.corpreport.models import ReportCategory
from emtools.corpreport.utils import get_locations


def snapshop_reporter(f, ts, ownerid):
    rc = ReportCollector(ownerid)
    (sales_center, logistics_center, offics,
     sales_points, purchase_points) = get_locations(ownerid)
    offices = set([station.solarSystemID for station in sales_center])
    logistics = set([station.solarSystemID for station in logistics_center])
    sales = set([station.solarSystemID for station in sales_points])

    add_balance(ts, rc)
    add_industryjobs(ts, rc)
    rc.merge_to(offices)
    add_assets(ts, rc)
    rc.merge_to(offices | logistics)
    add_marketorders(ts, rc)
    rc.merge_to(offices | logistics | sales)

    cache = {}
    def get_cost(hangar, type_):
        if type_.group.category.categoryName == 'Blueprint':
            if hangar == 'HIGH SECURITY':
                return type_.basePrice * 0.9
            else:
                return 0.0
        if type_ not in cache:
            cache[type_] = cost(ownerid, type_)
        return cache[type_]

    data = rc.get_value_tree(get_cost)
    report_global(f, data)
    report_systems(f, "Sales Center", offices, data)
    report_systems(f, "Logistics Center", logistics, data)
    report_systems(f, "Sales Points", sales, data)

def humane(obj, dosign=False):
    if isinstance(obj, int) or isinstance(obj, long):
        return humaneint(obj, dosign)
    elif isinstance(obj, float):
        return humanefloat(obj, dosign)
    else:
        return obj

def humanefloat(num, dosign):
    num = "%.2f" % float(num)
    return humaneint(num[:-3], dosign) + num[-3:]

def humaneint(num, dosign):
    num = str(long(num))
    if num[0] == "-":
        sign = "-"
        num = num[1:]
    elif dosign:
        sign = "+"
    else:
        sign = ""
    triple = []
    while True:
        if len(num) > 3:
            triple = [num[-3:]] + triple
            num = num[:-3]
        else:
            triple = [num] + triple
            break
    return sign + ",".join(triple)

def report_global(f, data):
    name = "Global"
    f.write("%s\n%s\n" % (name, len(name) * "="))
    for category, value in sorted(data.get(None, {}).items(),
                                  key=lambda x: x[1], reverse=True):
        f.write("- %s: %s\n" % (category, humane(value)))
    f.write("\n")

def report_systems(f, name, systems, data):
    systems = [SolarSystem.objects.get(solarSystemID=sysid)
               for sysid in set(systems)]
    f.write("%s\n%s\n" % (name, len(name) * "="))
    for system in sorted(systems, key=lambda x: x.solarSystemName):
        f.write("%s\n%s\n" % (system.solarSystemName,
                              len(system.solarSystemName) * "-"))
        for category, value in sorted(data.get(system, {}).items(),
                                      key=lambda x: x[1], reverse=True):
            f.write("- %s: %s\n" % (category, humane(value)))
        f.write("\n")


def add_balance(ts, rc):
    ownerid = rc.ownerid
    apitimestamp = Balance.objects.filter(
        apitimestamp__lt=ts, ownerid=ownerid
        ).order_by("-apitimestamp")[0].apitimestamp
    for balance in Balance.objects.filter(apitimestamp=apitimestamp,
                                          ownerid=ownerid):
        div = Division.objects.get(accountKey=balance.accountKey,
                                   ownerid=ownerid)
        if div.divisionconfig.usewallet:
            rc.add(div.walletname, balance.balance)

def add_industryjobs(ts, rc):
    ownerid = rc.ownerid
    apitimestamp = IndustryJob.objects.filter(
        apitimestamp__lt=ts, ownerid=ownerid
        ).order_by("-apitimestamp")[0].apitimestamp
    for job in IndustryJob.objects.filter(apitimestamp=apitimestamp,
                                          ownerid=ownerid):
        loc = Asset.objects.filter(ownerid=ownerid,
                                   itemID=job.installedItemLocationID,
                                   ).order_by("-apitimestamp")[0]
        item = InvItem(loc.locationID)
        rc.add(job.installedItemTypeID, job.installedItemQuantity,
               solarsystemid=item.solarSystemID,
               stationid=item.stationID)
        rc.add(job.outputTypeID, job.runs,
               solarsystemid=item.solarSystemID,
               stationid=item.stationID)

def add_marketorders(ts, rc):
    ownerid = rc.ownerid
    apitimestamp = MarketOrder.objects.filter(
        apitimestamp__lt=ts, ownerid=ownerid
        ).order_by("-apitimestamp")[0].apitimestamp
    for order in MarketOrder.objects.filter(apitimestamp=apitimestamp,
                                            ownerid=ownerid):
        order.stationID
        if order.bid:
            rc.add("Escrow", order.escrow, stationid=order.stationID)
        else:
            rc.add(order.typeID, order.volRemaining, stationid=order.stationID)

def add_assets(ts, collector):
    ownerid = collector.ownerid
    apitimestamp = Asset.objects.filter(
        apitimestamp__lt=ts, ownerid=ownerid
        ).order_by("-apitimestamp")[0].apitimestamp
    asset_list = Asset.objects.filter(apitimestamp=apitimestamp,
                                      ownerid=ownerid)
    office_type_id = Type.objects.get(typeName='Office').typeID
    offices = set()
    hangars = {}
    for asset in asset_list:
        if asset.typeID == office_type_id:
            offices.add(asset.id)
            hangars[asset.id] = None
            hangar = None
        elif asset.container_id in offices:
            hangars[asset.id] = asset.flag
            hangar = asset.flag
        elif asset.container_id in hangars:
            hangars[asset.id] = hangars[asset.container_id]
            hangar = hangars[asset.container_id]
        else:
            hangars[asset.id] = asset.flag
            hangar = asset.flag
        item = InvItem(asset.locationID)
        collector.add(asset.typeID, asset.quantity,
                      item.solarSystemID, item.stationID, hangar)

def get_flags(ownerid):
    result = {Flag.objects.get(flagName='CorpMarket').flagID: 'DELIVERIES'}
    for div in Division.objects.filter(ownerid=ownerid):
        if div.accountKey == 1000:
            flagname = 'Hangar'
        else:
            flagname = "CorpSAG%s" % (div.accountKey - 999)
        flagid = Flag.objects.get(flagName=flagname).flagID
        if div.divisionconfig.usehangar:
            result[flagid] = div.hangarname
    return result

class ReportCollector(object):
    def __init__(self, ownerid):
        self.ownerid = ownerid
        self.collection = {}
        self.staid2sysid = {}
        for sta in Station.objects.all():
            self.staid2sysid[sta.stationID] = sta.solarSystemID
        self.neighbors = {}
        c = connection.cursor()
        c.execute("SELECT fromsolarsystemid, tosolarsystemid "
                  "FROM ccp.mapsolarsystemjumps")
        for fromsys, tosys in c.fetchall():
            self.neighbors.setdefault(fromsys, [])
            self.neighbors[fromsys].append(tosys)

    def add(self, type_or_category, quantity,
            solarsystemid=None, stationid=None, flag=None):
        if solarsystemid is None and stationid is not None:
            solarsystemid = self.staid2sysid[stationid]
        self.collection.setdefault(solarsystemid, {})
        a = self.collection[solarsystemid]
        a.setdefault(flag, {})
        b = a[flag]
        b.setdefault(type_or_category, 0)
        b[type_or_category] += quantity

    def merge_to(self, target_system_ids):
        for sysid in self.collection.keys():
            if sysid is None:
                continue
            if sysid not in target_system_ids:
                target = self.find_closest(sysid, target_system_ids)
                for flag, contents in self.collection[sysid].items():
                    for typeID, quantity in contents.items():
                        self.add(typeID, quantity,
                                 solarsystemid=target, flag=flag)
                del self.collection[sysid]

    def get_tree(self):
        result = []
        flagid2hangar = get_flags(self.ownerid)
        types = {}
        categories = {}
        for systemid, contents in self.collection.items():
            if systemid is None:
                system = None
            else:
                system = SolarSystem.objects.get(solarSystemID=systemid)
            for flag, contents2 in contents.items():
                for type_or_category, quantity in contents2.items():
                    if isinstance(type_or_category, basestring):
                        category = type_or_category
                        typeID = None
                    else:
                        typeID = type_or_category
                        if typeID not in types:
                            types[typeID] = Type.objects.get(typeID=typeID)
                            try:
                                categories[typeID] = ReportCategory.objects.get(
                                    type=types[typeID]).category
                            except ReportCategory.DoesNotExist:
                                ReportCategory.objects.create(
                                    type=types[typeID],
                                    category='Unknown')
                                categories[typeID] = 'Unknown'
                        category = categories[typeID]
                    if flag is None or flag in flagid2hangar:
                        result.append((system,
                                       flagid2hangar.get(flag),
                                       category,
                                       types.get(typeID),
                                       quantity))
        return result

    def get_value_tree(self, get_cost):
        tree = {}
        for system, hangar, category, type_, quantity in self.get_tree():
            if type_ is None:
                cost = float(quantity)
            else:
                cost = get_cost(hangar, type_) * float(quantity)
            tree.setdefault(system, {})
            tree[system].setdefault(category, 0)
            tree[system][category] += cost
        return tree

    def find_closest(self, start, endlist):
        target = set(endlist)
        agenda = [(0, start)]
        visited = set()
        while len(agenda) > 0:
            distance, here = agenda[0]
            agenda = agenda[1:]
            if here in visited:
                continue
            visited.add(here)
            if here in target:
                return here
            for neighbor in self.neighbors.get(here, []):
                agenda.append((distance + 1, neighbor))
        return None
