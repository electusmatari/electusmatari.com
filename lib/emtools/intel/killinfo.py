# coding: utf-8

from emtools.ccpeve.ccpdb import get_moonid

import datetime
import logging

def is_characterid(itemid):
    return (3000000 <= itemid < 4000000 or # NPC
            90000000 <= itemid < 91000000 or # Old player
            100000000 <= itemid) # New player

def is_corporationid(itemid):
    return (1000000 <= itemid < 2000000 or # NPC
            98000000 <= itemid < 99000000 or # Old player corp
            100000000 <= itemid) # New player corp

def is_allianceid(itemid):
    return (99000000 <= itemid < 100000000 or # Old player alliance
            100000000 <= itemid) # New player alliance

def is_factionid(itemid):
    return 500000 <= itemid < 1000000


class Killinfo(object):
    def __init__(self):
        self.killid = None
        self.kill_internal_id = None
        self.solarsystemid = None
        self.killtime = None
        self.moonid = None
        # Victim
        self.victim = Victim()
        self.damagetaken = None
        self.shiptypeid = None
        # Attackers
        self.attackers = []
        # Items
        self.items = []

    def fix(self):
        try:
            self.fix_ccp_idiocies()
            self.fix_edk_idiocies()
        except:
            logging.exception("Exception during fix")
            raise

    def fix_ccp_idiocies(self):
        # Translating the alliance name that indicates "no alliance"
        # is awesome. Oh, it can also be "None" or "Unknown",
        # depending on whether it's the involved party or the victim.
        # Consistency is for the fearful.
        for p in [self.victim] + self.attackers:
            if (p.alliancename is not None and
                p.alliancename.lower() in [u'Неизвестно', u'неизвестно', u'het',
                                           u'unbekannt', u'keine',
                                           u'unknown', u'none']):
                p.alliancename = None
                p.allianceid = None
            if p.alliancename in [u'\u041d\u0415\u0422', u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e']:
                p.alliancename = None
                p.allianceid = None

    def fix_edk_idiocies(self):
        # EDK fucks up moon parsing a lot. Moons are not characters,
        # they're moons. It's hard, because EDK is dumb.
        if self.victim.charactername is not None and '- Moon ' in self.victim.charactername:
            self.victim.moonid = get_moonid(self.victim.charactername.strip())
            self.victim.characterid = None
            self.victim.charactername = None
        factions = {'amarr empire': (500003, 'Amarr Empire'),
                    'minmatar republic': (500002, 'Minmatar Republic'),
                    'gallente federation': (500004, 'Gallente Federation'),
                    'caldari state': (500001, 'Caldari State')
                    }
        for p in [self.victim] + self.attackers:
            # EDK fakes factions by treating them as alliances,
            # because EDK is dumb.
            if ((p.alliancename is not None and
                 p.alliancename.lower() in factions)):
                p.factionid, p.factionname = factions[p.alliancename.lower()]
                p.alliancename = ''
                p.allianceid = 0
            # EDK also often fucks up NPC name parsing, because EDK is dumb.
            if ((p.charactername is not None and
                 " - " in p.charactername)): # NPC
                p.charactername = ''
                p.characterid = 0
            # Oh, and EDK also often puts wrong values (like, typeIDs
            # or solarSystemIDs) into corporationid or characterid
            # fields, because EDK is dumb. Verifying allianceid for
            # good measure - you never know, you see, because EDK is
            # dumb.
            if p.allianceid is not None and not is_allianceid(p.allianceid):
                p.alliancename = ''
                p.allianceid = 0
            if p.corporationid is not None and not is_corporationid(p.corporationid):
                p.corporationname = ''
                p.corporationid = 0
            if p.characterid is not None and not is_characterid(p.characterid):
                p.characterid = 0
                p.charactername = ''

class Person(object):
    def __init__(self, characterid=None, charactername=None,
                 corporationid=None, corporationname=None,
                 allianceid=None, alliancename=None,
                 factionid=None, factionname=None):
        self.characterid = characterid
        self.charactername = charactername
        self.corporationid = corporationid
        self.corporationname = corporationname
        self.allianceid = allianceid
        self.alliancename = alliancename
        self.factionid = factionid
        self.factionname = factionname

class Victim(Person):
    def __init__(self, damagetaken=None, shiptypeid=None, **kwargs):
        super(Victim, self).__init__(**kwargs)
        self.damagetaken = damagetaken
        self.shiptypeid = shiptypeid

class Attacker(Person):
    def __init__(self, security=None, damagedone=None, finalblow=None,
                 weapontypeid=None, shiptypeid=None, **kwargs):
        super(Attacker, self).__init__(**kwargs)
        self.security = security
        self.damagedone = damagedone
        self.finalblow = finalblow
        self.weapontypeid = weapontypeid
        self.shiptypeid = shiptypeid

class Item(object):
    def __init__(self, typeid=None, typename=None, flag=None,
                 location=None, qtydropped=None, qtydestroyed=None,
                 singleton=None):
        self.typeid = typeid
        self.typename = typename
        self.flag = flag
        self.location = location
        self.qtydropped = qtydropped
        self.qtydestroyed = qtydestroyed
        self.singleton = singleton

def strn(obj):
    if obj is None or obj == '':
        return None
    if not isinstance(obj, basestring):
        obj = str(obj)
    try:
        return unicode(obj)
    except UnicodeDecodeError:
        pass
    try:
        return obj.decode("utf-8")
    except UnicodeDecodeError:
        return obj.decode("latin-1")

def intn(obj):
    if obj is None or obj == '':
        return None
    else:
        return int(obj)

from xml.etree import ElementTree

def parse_api_page(xml):
    tree = ElementTree.fromstring(xml)
    result = []
    for row in tree.findall("result/rowset/row"):
        ki = Killinfo()
        ki.killid = intn(row.get('killID'))
        ki.kill_internal_id = intn(row.get('killInternalID'))
        if ki.kill_internal_id is None:
            ki.kill_internal_id = ki.killid
            ki.killid = None
        ki.solarsystemid = intn(row.get('solarSystemID'))
        ki.killtime = datetime.datetime.strptime(row.get('killTime'),
                                                 "%Y-%m-%d %H:%M:%S")
        ki.moonid = intn(row.get('moonID'))

        victim = row.find("victim")
        ki.victim.characterid = intn(victim.get('characterID'))
        ki.victim.charactername = strn(victim.get('characterName'))
        ki.victim.corporationid = intn(victim.get('corporationID'))
        ki.victim.corporationname = strn(victim.get('corporationName'))
        ki.victim.allianceid = intn(victim.get('allianceID'))
        ki.victim.alliancename = strn(victim.get('allianceName'))
        ki.victim.factionid = intn(victim.get('factionID'))
        ki.victim.factionname = strn(victim.get('factionName'))
        ki.victim.damagetaken = intn(victim.get('damageTaken'))
        ki.victim.shiptypeid = intn(victim.get('shipTypeID'))

        def find_rows(tree, name):
            for rowset in tree.findall("rowset"):
                if rowset.get('name') == name:
                    return rowset.findall("row")
            return []

        for attacker in find_rows(row, 'attackers'):
            att = Attacker()
            att.characterid = intn(attacker.get('characterID'))
            att.charactername = strn(attacker.get('characterName'))
            att.corporationid = intn(attacker.get('corporationID'))
            att.corporationname = strn(attacker.get('corporationName'))
            att.allianceid = intn(attacker.get('allianceID'))
            att.alliancename = strn(attacker.get('allianceName'))
            att.factionid = intn(attacker.get('factionID'))
            att.factionname = strn(attacker.get('factionName'))
            att.security = attacker.get('securityStatus')
            att.damagedone = intn(attacker.get('damageDone'))
            att.finalblow = bool(attacker.get('finalBlow'))
            att.weapontypeid = intn(attacker.get('weaponTypeID'))
            att.shiptypeid = intn(attacker.get('shipTypeID'))
            ki.attackers.append(att)
        for item in find_rows(row, 'items'):
            i = Item()
            i.typeid = intn(item.get('typeID'))
            i.flag = intn(item.get('flag'))
            i.qtydropped = intn(item.get('qtyDropped'))
            i.qtydestroyed = intn(item.get('qtyDestroyed'))
            i.singleton = item.get('singleton')
            ki.items.append(i)
        ki.fix()
        result.append(ki)
    return result

# WARNING!
# This assumes an eveapi.py kill object. But eveapi.py can not parse
# EDK output, as EDK does not adhere to the broken XML semantics
# eveapi.py assumes.
def parse_eveapiinfo(kill):
    ki = Killinfo()
    ki.killid = intn(kill.killID)
    ki.kill_internal_id = intn(getattr(kill, 'killInternalID', None))
    if ki.kill_internal_id is None:
        ki.kill_internal_id = ki.killid
        ki.killid = None
    ki.solarsystemid = intn(kill.solarSystemID)
    ki.killtime = datetime.datetime.utcfromtimestamp(kill.killTime)
    ki.moonid = intn(kill.moonID)
    ki.victim.characterid = intn(kill.victim.characterID)
    ki.victim.charactername = strn(kill.victim.characterName)
    ki.victim.corporationid = intn(kill.victim.corporationID)
    ki.victim.corporationname = strn(kill.victim.corporationName)
    ki.victim.allianceid = intn(kill.victim.allianceID)
    ki.victim.alliancename = strn(kill.victim.allianceName)
    ki.victim.factionid = intn(kill.victim.factionID)
    ki.victim.factionname = strn(getattr(kill.victim, 'factionName', None))
    for attacker in kill.attackers:
        att = Attacker()
        att.characterid = intn(attacker.characterID)
        att.charactername = strn(attacker.characterName)
        att.corporationid = intn(attacker.corporationID)
        att.corporationname = strn(attacker.corporationName)
        att.allianceid = intn(attacker.allianceID)
        att.alliancename = strn(attacker.allianceName)
        att.security = attacker.securityStatus
        att.damagedone = intn(attacker.damageDone)
        att.finalblow = bool(attacker.finalBlow)
        att.weapontypeid = intn(attacker.weaponTypeID)
        att.shiptypeid = intn(attacker.shipTypeID)
        ki.attackers.append(att)
    if hasattr(kill, 'items'):
        for item in kill.items:
            i = Item()
            i.typeid = intn(item.typeID)
            i.flag = intn(item.flag)
            i.qtydropped = intn(item.qtyDropped)
            i.qtydestroyed = intn(item.qtyDestroyed)
            ki.items.append(item)
    return ki

def parse_textinfo(text):
    raise RuntimeError('parse_textinfo() not implemented yet')

