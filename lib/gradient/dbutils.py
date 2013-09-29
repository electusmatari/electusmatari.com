from django.db import connection

from emtools.ccpeve.models import APIKey, apiroot

THEFORGE = 10000002
MOLDENHEATH = 10000028
HEIMATAR = 10000030
METROPOLIS = 10000042

def get_typeid(typename):
    c = connection.cursor()
    c.execute("SELECT typeid FROM ccp.invtypes WHERE "
              "LOWER(typename) = LOWER(%s)",
              (typename,))
    if c.rowcount > 0:
        return c.fetchone()[0]
    else:
        return None

def get_typename(typeid):
    c = connection.cursor()
    c.execute("SELECT typename FROM ccp.invtypes WHERE typeid = %s",
              (typeid,))
    if c.rowcount > 0:
        return c.fetchone()[0]
    else:
        return None

def get_itemid(itemname):
    c = connection.cursor()
    c.execute("SELECT itemid FROM ccp.invuniquenames WHERE "
              "LOWER(itemname) = LOWER(%s)",
              (itemname,))
    if c.rowcount > 0:
        return c.fetchone()[0]
    else:
        return None

def get_itemname(itemid):
    c = connection.cursor()
    c.execute("SELECT itemname FROM ccp.invnames WHERE "
              "itemid = %s",
              (itemid,))
    if c.rowcount > 0:
        return c.fetchone()[0]
    else:
        return None

def get_systemfaction(systemid):
    c = connection.cursor()
    c.execute("SELECT COALESCE(s.factionid, c.factionid, r.factionid) "
              "FROM ccp.mapsolarsystems s "
              "     INNER JOIN ccp.mapconstellations c "
              "       ON s.constellationid = c.constellationid "
              "     INNER JOIN ccp.mapregions r "
              "       ON c.regionid = r.regionid "
              "WHERE s.solarsystemid = %s",
              (systemid,))
    if c.rowcount > 0:
        return c.fetchone()[0]
    else:
        return None
    
def get_stationsystem(stationid):
    c = connection.cursor()
    c.execute("SELECT solarsystemid FROM ccp.stastations WHERE "
              "stationid = %s",
              (stationid,))
    if c.rowcount > 0:
        return c.fetchone()[0]
    else:
        return None

def get_systemregion(systemid):
    c = connection.cursor()
    c.execute("SELECT regionid FROM ccp.mapsolarsystems WHERE "
              "solarsystemid = %s",
              (systemid,))
    if c.rowcount > 0:
        return c.fetchone()[0]
    else:
        return None

def system_distance(systemid1, systemid2):
    c = connection.cursor()
    c.execute("SELECT fromsolarsystemid, tosolarsystemid "
              "FROM ccp.mapsolarsystemjumps")
    jumps = {}
    for a, b in c.fetchall():
        jumps.setdefault(a, [])
        jumps[a].append(b)
    agenda = [(systemid1, 0)]
    visited = set()
    while len(agenda) > 0:
        (here, distance) = agenda[0]
        agenda = agenda[1:]
        if here == systemid2:
            return distance
        if here in visited:
            continue
        visited.add(here)
        agenda.extend((neighbor, distance + 1)
                      for neighbor in jumps[here])
    return None

def reprocess(typeid):
    c = connection.cursor()
    c.execute("SELECT portionsize FROM ccp.invtypes WHERE typeid = %s",
              (typeid,))
    portionsize = c.fetchone()[0]
    c.execute("SELECT materialtypeid, quantity FROM ccp.invtypematerials "
              "WHERE typeid = %s", (typeid,))
    return [(mattypeid, quantity / float(portionsize))
            for (mattypeid, quantity) in c.fetchall()]

def get_membername(charid):
    grd = APIKey.objects.get(name='Gradient').corp()
    for row in grd.MemberTracking().members:
        if row.characterID == charid:
            return row.name
    api = apiroot()
    return api.eve.CharacterName(ids=charid).characters[0].name
