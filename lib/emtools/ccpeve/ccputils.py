# config.BulkData.locations
# (0L, '(none)')
# config.StaticLocations
# StaticLocations = marshal.Load(file('bulkdata/9992.cache').read())
# [(x.locationID, x.locationName) for x in StaticLocations[1].GetObject()]

class InvItem(object):
    def __init__(self, itemID):
        self.id = itemID
        self.itemID = itemID
        self.classname = self._classname()

    def __repr__(self):
        return "<InvItem %s (%s)>" % (self.itemID, self.classname)

    @property
    def stationID(self):
        if self.classname == 'Station':
            return self.itemID
        elif self.classname == 'OfficeFolder':
            if self.itemID < 67000000: # Normal station
                return self.itemID - 6000001
            else: # Outpost
                return self.itemID - 6000000
        else:
            return None

    @property
    def solarSystemID(self):
        if self.classname == 'Solar System':
            return self.itemID
        else:
            return None

    def _classname(self):
        itemid = self.itemID
        if itemid in (6, 8, 10, 23, 25) or 100 < itemid < 2000:
            return 'JunkLocation'
        elif itemid < 10000:
            return '#System' # NOT Solar System
        # 10000 <= itemid < 500000
        elif 500000 <= itemid < 1000000:
            return 'Faction'
        elif 1000000 <= itemid < 2000000:
            return 'Corporation'
        # 2000000 <= itemid < 3000000
        elif 3000000 <= itemid < 4000000:
            return 'Character'
        # 4000000 <= itemid < 10000000
        elif 10000000 <= itemid < 20000000:
            return 'Region'
        elif 20000000 <= itemid < 30000000:
            return 'Constellation'
        elif 30000000 <= itemid < 40000000:
            return 'Solar System'
        elif 40000000 <= itemid < 50000000:
            # Sun, Planet, Asteroid Belt, Moon, Secondary Sun
            return 'Celestial'
        elif 50000000 <= itemid < 60000000:
            return 'Stargate'
        elif 60000000 <= itemid < 61000000:
            return 'Station'
        elif 61000000 <= itemid < 64000000:
            return 'Outpost'
        elif 64000000 <= itemid < 66000000:
            return 'Trading' # ?? cfg.IsTrading
        elif 66000000 <= itemid < 68000000:
            return 'OfficeFolder'
        elif 68000000 <= itemid < 70000000:
            return 'FactoryFolder'
        elif 70000000 <= itemid < 80000000:
            return 'Asteroid'
        elif 80000000 <= itemid < 80100000:
            return 'ControlBunker'
        # 80100000 <= itemid < 81000000
        elif 81000000 <= itemid < 82000000:
            return 'WorldSpace'
        # 82000000 <= itemid < 90000000
        elif 90000000 <= itemid < 91000000:
            return 'Character' # Old, newer characters get a Player Item
        # Seen characters > 91000000, too!
        # 91000000 <= itemid < 98000000
        elif 98000000 <= itemid < 99000000:
            return 'Corporation' # Old, newer corporations get a Player Item
        elif 99000000 <= itemid < 100000000:
            return 'Alliance' # Old, newer alliances get a Player Item
        elif 100000000 <= itemid < 9000000000000000000L:
            # Corporation, alliance, ...
            return 'Player Item'
        elif 9000000000000000000L <= itemid:
            return 'Fake Item'
        else:
            raise RuntimeError("Unknown locationID %s" % itemid)

def is_valid_characterid(itemid):
    return (3000000 <= itemid < 4000000 or # NPCs / agents
            90000000 <= itemid < 98000000 or # Old player characters
            100000000 <= itemid)

def is_valid_corporationid(itemid):
    return (1000000 <= itemid < 2000000 or # NPC corps
            98000000 <= itemid < 99000000 or # Old player corps
            100000000 <= itemid)

def is_valid_allianceid(itemid):
    return (99000000 <= itemid < 100000000 or # Old alliances
            100000000 <= itemid)

def is_valid_factionid(itemid):
    return 500000 <= itemid < 1000000
