from django.db import connection

def get_systemid(name):
    c = connection.cursor()
    c.execute("SELECT solarsystemid FROM ccp.mapsolarsystems "
              "WHERE solarsystemname = %s",
              (name,))
    if c.rowcount == 1:
        return c.fetchone()[0]
    else:
        return None

def get_stationid(name):
    c = connection.cursor()
    c.execute("SELECT stationid FROM ccp.stastations WHERE stationname = %s",
              (name,))
    if c.rowcount == 1:
        return c.fetchone()[0]
    else:
        return None

def get_regionname(regionid):
    c = connection.cursor()
    c.execute("SELECT regionname FROM ccp.mapregions WHERE regionid = %s",
              (regionid,))
    if c.rowcount == 1:
        return c.fetchone()[0]
    else:
        return None

def get_typename(typeid):
    c = connection.cursor()
    c.execute("SELECT typename FROM ccp.invtypes WHERE typeid = %s",
              (typeid,))
    if c.rowcount == 1:
        return c.fetchone()[0]
    else:
        return None

def get_typeid(typename):
    c = connection.cursor()
    c.execute("SELECT typeid FROM ccp.invtypes WHERE typename = %s",
              (typename,))
    if c.rowcount == 1:
        return c.fetchone()[0]
    else:
        return None

def get_locator_agents(system, maxjumps):
    result = []
    for here, jumps in systemrange(system, maxjumps):
        for agent in locatoragents(here):
            agent['jumps'] = jumps
            result.append(agent)
    return sorted(result, key=lambda agent: agent['jumps'])

def get_moonid(moonname):
    c = connection.cursor()
    c.execute("""
SELECT itemid FROM ccp.mapdenormalize WHERE LOWER(itemname) = LOWER(%s)
""", (moonname,))
    if c.rowcount > 0:
        return c.fetchone()[0]
    else:
        return None

def locatoragents(systemname):
    c = connection.cursor()
    c.execute("""
SELECT sys.solarsystemid, sys.solarsystemname, a.level, f.factionname,
       st.stationName, st.stationid
FROM ccp.agtAgents a
     INNER JOIN ccp.staStations st
       ON a.locationID = st.stationID
     INNER JOIN ccp.mapSolarSystems sys
       ON st.solarSystemID = sys.solarSystemID
     INNER JOIN ccp.crpnpccorporations corp
       ON st.corporationid = corp.corporationid
     INNER JOIN ccp.chrfactions f
       ON corp.factionid = f.factionid
WHERE a.islocator = 1
  AND sys.solarSystemName = %s
""", (systemname,))
    for systemid, systemname, level, factionname, stationname, stationid in c.fetchall():
        if factionname in ('Jove Empire', 'CONCORD Assembly'):
            continue
        if level >= 3:
            yield {'systemid': systemid,
                   'systemname': systemid,
                   'level': level,
                   'factionname': factionname,
                   'stationname': stationname,
                   'stationid': stationid}

def systemrange(system, maxjumps):
    c = connection.cursor()
    c.execute("SELECT f.solarsystemname, t.solarsystemname "
              "FROM ccp.mapsolarsystemjumps j "
              "     INNER JOIN ccp.mapsolarsystems f "
              "       ON j.fromsolarsystemid = f.solarsystemid "
              "     INNER JOIN ccp.mapsolarsystems t "
              "       ON j.tosolarsystemid = t.solarsystemid")
    neighbors = {}
    for fromsys, tosys in c.fetchall():
        neighbors.setdefault(fromsys, [])
        neighbors[fromsys].append(tosys)
    if system not in neighbors:
        return
    agenda = [(system, 0)]
    visited = set()
    while len(agenda) > 0:
        ((here, jumps), agenda) = (agenda[0], agenda[1:])
        if here in visited:
            continue
        visited.add(here)
        yield here, jumps
        if jumps < maxjumps:
            agenda.extend([(neighborname, jumps + 1)
                           for neighborname in neighbors[here]
                           if neighborname not in visited])
