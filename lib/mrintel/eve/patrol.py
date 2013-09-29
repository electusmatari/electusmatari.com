import datetime

from mrintel.eve.dbutils import DBConnection
from mrintel.eve import api

MINMATAR_REPUBLIC = 500002
AMARR_EMPIRE = 500003

def patrol(startsystem, maxlength):
    db = DBConnection()
    systems = db.get_interesting_systems_for_hot()
    apiroot = api.root()
    kills = []
    data = apiroot.map.Kills()
    datatime = datetime.datetime.utcfromtimestamp(data.dataTime)
    for row in data.solarSystems:
        if (row.shipKills > 0 and
            row.solarSystemID in systems
            ):
            kills.append((row.shipKills, row.solarSystemID))
    killdict = dict((sysid, nkills) for (nkills, sysid) in kills)
    kills.sort(key=lambda elt: (-elt[0], elt[1]))
    return patrol_generic(db, startsystem, maxlength, systems, kills)

def patrolcontested(startsystem, maxlength):
    db = DBConnection()
    systems = db.get_interesting_systems_for_hot()
    apiroot = api.root()
    contested = []
    for row in apiroot.map.FacWarSystems().solarSystems:
        if ((row.owningFactionID in (MINMATAR_REPUBLIC, AMARR_EMPIRE) or
             row.occupyingFactionID in (MINMATAR_REPUBLIC, AMARR_EMPIRE)
             ) and
            row.contested == 'True'
            ):
            contested.append((0, row.solarSystemID))
    return patrol_generic(db, startsystem, maxlength, systems, contested)

def patrol_generic(db, startsystem, maxlength, systemid2name, interesting):
    result = db.execute("select itemid, itemname from ccp.invnames where "
                        "lower(itemname) = lower(%s)", (startsystem,))
    if len(result) == 0:
        return "Can't find system {0}.".format(startsystem)
    startsystemid, startsystem = result[0]
    systemid2name[startsystemid] = startsystem
    idict = dict((sysid, info) for (info, sysid) in interesting)
    patrol_route, jumps = find_route(db, startsystemid, maxlength,
                                     [sysid for (info, sysid) in interesting
                                      if sysid != startsystemid])
    return ("{jumps} jumps: ".format(jumps=jumps) +
            ", ".join((systemid2name[sysid] if idict.get(sysid, 0) == 0
                      else "{0} ({1})".format(systemid2name[sysid],
                                              idict[sysid]))
                     for sysid in patrol_route))

def find_route(db, startsystemid, maxlength, optional_systems):
    current_anchors = [startsystemid]
    last_route = [startsystemid]
    last_length = 0
    for sysid in optional_systems:
        this_route, length = shortest_route(db, current_anchors + [sysid],
                                            maxlength)
        if length < 0 or length > maxlength:
            continue
        current_anchors.append(sysid)
        last_route = this_route
        last_length = length
    return ([sysid for sysid in last_route
             if sysid == startsystemid or sysid in optional_systems],
            last_length)

def shortest_route(db, sysidlist, maxlength):
    """
    Return the shortest route that includes all elements of sysidlist.

    NP sucks. We start at sysidlist[0], and then use hillclimbing.
    """
    route = [sysidlist[0]]
    agenda = set(sysidlist[1:])
    length = 0
    while agenda:
        if length > maxlength:
            return [], -1
        distances = [(db.distance(route[-1], sysid), sysid)
                     for sysid in agenda]
        distances.sort()
        nextsysid = distances[0][1]
        route.append(nextsysid)
        length += distances[0][0]
        agenda.remove(nextsysid)
    return route, length
