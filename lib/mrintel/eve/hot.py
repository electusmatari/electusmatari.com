import datetime

from mrintel.eve.dbutils import DBConnection
from mrintel.eve import api

def hot():
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
            kills.append((row.shipKills, systems[row.solarSystemID]))
    kills.sort(key=lambda elt: (-elt[0], elt[1]))
    return (", ".join("{1} ({0})".format(*row) for row in kills[:20])
            +
            " (from {0})".format(datatime.strftime("%Y-%m-%d %H:%M:%S")))
