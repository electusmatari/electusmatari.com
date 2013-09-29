from mrintel.eve.dbutils import DBConnection
from mrintel.eve import api

METER_TO_AU = 6.68458134e-12

def plural(num, singular="", plural="s"):
    if num == 1:
        return singular
    else:
        return plural

def format_reply(info):
    """
    Turn an info dict into an appropriate IRC description.
    """
    if info['type'] == 'unknown':
        return ("I can't find any information on {0}, I'm afraid"
                .format(info['name']))
    elif info['type'] == 'region':
        s = ("Region {name} ({facname}) with "
             "{numhighsec} high-sec and {numlowsec} low-sec system{sysplural} "
             "in {numconstellation} constellation{constplural}."
             .format(facname=info['factionname'] or "capsuleer sovereignty",
                     sysplural=plural(info['numhighsec'] + info['numlowsec']),
                     constplural=plural(info['numconstellation']),
                     **info))
        if info['numfacwar'] > 0:
            s += (" {numfacwar} system{sysplural} are in the war zone."
                  .format(sysplural=plural(info['numfacwar']),
                                           **info))
        return s
    elif info['type'] == 'constellation':
        s = ("Constellation {name}, {regionname} ({facname}) with "
             "{numhighsec} high-sec and {numlowsec} low-sec "
             "system{sysplural}."
             .format(facname=info['factionname'] or "capsuleer sovereignty",
                     sysplural=plural(info['numhighsec'] + info['numlowsec']),
                     **info))
        if info['numfacwar'] > 0:
            s += (" {numfacwar} system{sysplural} are in the war zone."
                  .format(sysplural=plural(info['numfacwar']),
                          **info))
        return s
    elif info['type'] == 'solarsystem':
        s = ("{name} ({security:.1f}), {constellationname}, {regionname} "
              "({facname}".format(facname=info['factionname'] or
                                  "capsuleer sovereignty",
                                  **info))
        if info['facwar']:
            if 'occupiedby' in info:
                s += ", occupied by {occupiedby}".format(**info)
            else:
                s += ", war zone"
            if info.get('contested', False):
                s += ", contested"
            else:
                s += ", not contested"
            if 'vp' in info:
                perc = (info['vp'] * 100) / info['vpthreshold']
                s += (" with {vp} VP / {perc} % at {ts}"
                      .format(perc=perc,
                              ts=info['vptimestamp'].strftime("%Y-%m-%d %H:%M:%S"),
                              **info))

        s += ("), with {numgates} gate{gateplural}, "
              "{numstations} station{staplural}, {numbelts} belt{beltplural}, "
              "and {numicefields} ice field{iceplural}. The system is "
              "{diameter:.2f} AU large."
              .format(gateplural=plural(info['numgates']),
                      staplural=plural(info['numstations']),
                      beltplural=plural(info['numbelts']),
                      iceplural=plural(info['numicefields']),
                      **info))
        return s
    elif info['type'] == 'w-space':
        s = ("Solar system {name} in class {class} unknown space."
             .format(**info))
        if info['anomaly']:
            s += " Anomaly {anomaly} reported.".format(**info)
        return s
    elif info['type'] == 'wormhole':
        return ("Wormhole {name}, leads to class {wormholeTargetSystemClass} "
                "({classdesc}). "
                "Maximum jumpable mass {wormholeMaxJumpMass:,d} kg, "
                "maximum stable mass {wormholeMaxStableMass:,d} kg. "
                "Maximum stable time {stable:.1f} hours. "
                "Distribution {wormholeTargetDistribution}."
                .format(stable=info['wormholeMaxStableTime'] / 60.0,
                        classdesc=WHCLASSDESC.get(
                    info['wormholeTargetSystemClass'], '?'),
                        **info))
    elif info['type'] == 'K162':
        return ("Wormhole endpoint, codenamed K162. This can lead anywhere.")
    elif info['type'] == 'agent':
        return ("{name} ({agenttype}), L{level} {division} agent "
                "of {corporation}, {corpfaction}.".format(**info))
    elif info['type'] == 'npccorp':
        return ("Non-capsuleer corporation {name}, {faction}."
                .format(**info))
    elif info['type'] == 'faction':
        s = ("Faction {name} with sovereignty in {numsystems} systems."
             .format(**info))
        if info['numoccupied'] > 0 or info['numoccupiee'] > 0:
            s += (" {numoccupied} foreign system{occplural} occupied, "
                  "{numoccupiee} system{occeeplural} occupied by enemies."
                  .format(occplural=plural(info['numoccupied']),
                          occeeplural=plural(info['numoccupiee']),
                          **info))
        return s
    elif info['type'] == 'pilot':
        s = ("{name}, security {security:.1f}, {race} {bloodline}"
             .format(**info))
        if info['charstanding'] != 0:
            s += " ({0:+d})".format(info['charstanding'])
        s += ", {corporation} [{corpticker}]".format(**info)
        if info['corpstanding'] != 0:
            s += " ({0:+d})".format(info['corpstanding'])
        if info['alliance']:
            s += ", {alliance} <{allianceticker}>".format(**info)
            if info['allystanding'] != 0:
                s += " ({0:+d})".format(info['allystanding'])
        if 'militia' in info:
            s += ", member of the {militia} militia".format(**info)
        s += "."
        return s
    elif info['type'] == 'corp':
        s = "{name} [{ticker}]".format(**info)
        if info['corpstanding'] != 0:
            s += " ({0:+d})".format(info['corpstanding'])
        s += (", {size} member{memberplural}"
              .format(memberplural=plural(info['size']),
                      **info))
        if info['alliance']:
            s += ", {alliance} <{allianceticker}>".format(**info)
            if info['allystanding'] != 0:
                s += " ({0:+d})".format(info['allystanding'])
        if 'militia' in info:
            s += ", member of the {militia} militia".format(**info)
        s += "."
        return s
    elif info['type'] == 'alliance':
        s = "{name} <{allianceticker}>".format(**info)
        if info['allystanding'] != 0:
            s += " ({0:+d})".format(info['allystanding'])
        s += (", {size} member{memberplural}"
              .format(memberplural=plural(info['size']),
                      **info))
        if 'militia' in info:
            s += ", member of the {militia} militia".format(**info)
        s += "."
        return s
    else:
        return ("Tell Arkady to implement formatting of {0} infos."
                .format(info['type']))

def iteminfo(itemname):
    """
    Return an info dict about this item.
    """
    db = DBConnection()
    return (info_region(db, itemname) or
            info_constellation(db, itemname) or
            info_solarsystem(db, itemname) or
            info_wormhole(db, itemname) or
            info_agent(db, itemname) or
            info_npccorp(db, itemname) or
            info_faction(db, itemname) or
            info_character(db, itemname) or
            info_corporation(db, itemname) or
            info_alliance(db, itemname) or
            {'name': itemname,
             'type': 'unknown'})


def info_region(db, itemname):
    result = db.execute("""
SELECT r.regionname,
       r.regionid,
       n.itemname,
       (SELECT COUNT(*) FROM ccp.mapconstellations c
        WHERE c.regionid = r.regionid),
       (SELECT COUNT(*) FROM ccp.mapsolarsystems s
        WHERE s.regionid = r.regionid AND s.security >= 0.45),
       (SELECT COUNT(*) FROM ccp.mapsolarsystems s
        WHERE s.regionid = r.regionid
              AND s.security < 0.45 AND security >= 0.0),
       (SELECT COUNT(*) FROM ccp.warcombatzonesystems wcs
        INNER JOIN ccp.mapsolarsystems s
          ON wcs.solarsystemid = s.solarsystemid
        WHERE s.regionid = r.regionid)
FROM ccp.mapregions r
     LEFT JOIN ccp.invnames n
       ON r.factionid = n.itemid
WHERE LOWER(r.regionname) = LOWER(%s)
""", (itemname,))
    if len(result) != 1:
        return None
    (regionname, regionid, factionname, numconst,
     numhigh, numlow, numfw) = result[0]
    return {'type': 'region',
            'name': regionname,
            'itemid': regionid,
            'factionname': factionname,
            'numconstellation': numconst,
            'numhighsec': numhigh,
            'numlowsec': numlow,
            'numfacwar': numfw}


def info_constellation(db, itemname):
    result = db.execute("""
SELECT c.constellationname,
       c.constellationid,
       n.itemname,
       r.regionname,
       (SELECT COUNT(*) FROM ccp.mapsolarsystems s
        WHERE s.constellationid = c.constellationid AND s.security >= 0.45),
       (SELECT COUNT(*) FROM ccp.mapsolarsystems s
        WHERE s.constellationid = c.constellationid
              AND s.security < 0.45 AND security >= 0.0),
       (SELECT COUNT(*) FROM ccp.warcombatzonesystems wcs
        INNER JOIN ccp.mapsolarsystems s
          ON wcs.solarsystemid = s.solarsystemid
        WHERE s.constellationid = c.constellationid)
FROM ccp.mapconstellations c
     INNER JOIN ccp.mapregions r
       ON c.regionid = r.regionid
     LEFT JOIN ccp.invnames n
       ON n.itemid = COALESCE(c.factionid, r.factionid)
WHERE LOWER(c.constellationname) = LOWER(%s)
""", (itemname,))
    if len(result) != 1:
        return None
    (constellationname, constellationid, factionname, regionname,
     numhigh, numlow, numfw) = result[0]
    return {'type': 'constellation',
            'name': constellationname,
            'itemid': constellationid,
            'factionname': factionname,
            'regionname': regionname,
            'numhighsec': numhigh,
            'numlowsec': numlow,
            'numfacwar': numfw}


def info_solarsystem(db, itemname):
    result = db.execute("""
SELECT s.solarsystemname,
       s.solarsystemid,
       s.security,
       n.itemname,
       c.constellationname,
       c.constellationid,
       r.regionname,
       r.regionid
FROM ccp.mapsolarsystems s
     INNER JOIN ccp.mapconstellations c
       ON s.constellationid = c.constellationid
     INNER JOIN ccp.mapregions r
       ON c.regionid = r.regionid
     LEFT JOIN ccp.invnames n
       ON n.itemid = COALESCE(s.factionid, c.factionid, r.factionid)
WHERE LOWER(s.solarsystemname) = LOWER(%s)
""", (itemname,))
    if len(result) != 1:
        return None
    (sysname, sysid, security, factionname,
     constname, constid, regionname, regionid) = result[0]
    info = {'type': 'solarsystem',
            'name': sysname,
            'itemid': sysid,
            'security': security,
            'factionname': factionname,
            'constellationname': constname,
            'regionname': regionname}
    result = db.execute("SELECT COUNT(*) FROM ccp.mapsolarsystemjumps "
                        "WHERE fromsolarsystemid = %s", (sysid,))
    info['numgates'] = result[0][0]
    result = db.execute("SELECT COUNT(*) FROM ccp.mapdenormalize d "
                        "INNER JOIN ccp.invtypes t "
                        "  ON t.typeid = d.typeid "
                        "WHERE d.solarsystemid = %s "
                        "  AND t.typename = 'Asteroid Belt'",
                        (sysid,))
    info['numbelts'] = result[0][0]
    result = db.execute("SELECT COUNT(*) FROM ccp.mapdenormalize d "
                        "INNER JOIN ccp.invtypes t "
                        "  ON t.typeid = d.typeid "
                        "WHERE d.solarsystemid = %s "
                        "  AND t.typename = 'Ice Field'",
                        (sysid,))
    info['numicefields'] = result[0][0]
    result = db.execute("SELECT COUNT(*) FROM ccp.stastations "
                        "WHERE solarsystemid = %s",
                        (sysid,))
    info['numstations'] = result[0][0]
    result = db.execute("SELECT COUNT(*) FROM ccp.warcombatzonesystems "
                        "WHERE solarsystemid = %s", (sysid,))
    if result[0][0] == 0:
        info['facwar'] = False
    else:
        info['facwar'] = True
        apiroot = api.root()
        fws = apiroot.map.FacWarSystems()
        for row in fws.solarSystems:
            if row.solarSystemID == sysid:
                if row.occupyingFactionID > 0:
                    result = db.execute("SELECT itemname FROM ccp.invnames "
                                        "WHERE itemid = %s",
                                        (row.occupyingFactionID,))
                    info['occupiedby'] = result[0][0]
                info['contested'] = row.contested == 'True'
                break
        result = db.execute("SELECT cachetimestamp, victorypoints, threshold "
                            "FROM uploader_facwarsystem "
                            "WHERE solarsystemid = %s",
                            (sysid,))
        if len(result) > 0:
            info['vptimestamp'] = result[0][0]
            info['vp'] = result[0][1]
            info['vpthreshold'] = result[0][2]
    result = db.execute("""
SELECT SQRT((a.x - b.x)^2 + (a.y - b.y)^2 + (a.z - b.z)^2)
FROM ccp.mapdenormalize a
     INNER JOIN ccp.mapdenormalize b
       ON a.solarsystemid = b.solarsystemid
WHERE a.solarsystemid = %s
ORDER BY SQRT DESC
LIMIT 1
""", (sysid,))
    info['diameter'] = result[0][0] * METER_TO_AU
    if 11000024 <= regionid <= 11000029:
        info['type'] = 'w-space'
        info['class'] = '?'
        info['anomaly'] = None
        for locid in [sysid, constid, regionid]:
            result = db.execute("SELECT wormholeclassid "
                                "FROM ccp.maplocationwormholeclasses "
                                "WHERE locationid = %s", (locid,))
            if len(result) == 1:
                info['class'] = result[0][0]
                break
        result = db.execute("SELECT t.typename "
                            "FROM ccp.mapdenormalize d "
                            "     INNER JOIN ccp.invtypes t "
                            "       ON d.typeid = t.typeid "
                            "     INNER JOIN ccp.invgroups g "
                            "       ON g.groupid = t.groupid "
                            "WHERE d.solarsystemid = %s "
                            "  AND g.groupname = 'Secondary Sun'",
                            (sysid,))
        if len(result) > 0:
            info['anomaly'] = result[0][0]
    return info


def info_wormhole(db, itemname):
    if itemname.upper() == 'K162':
        return {'type': 'K162'}

    if itemname.upper() not in WORMHOLEINFO:
        return None
    info = {'type': 'wormhole',
            'name': itemname.upper()}
    info.update(WORMHOLEINFO[itemname.upper()])
    return info


def info_agent(db, itemname):
    result = db.execute("""
SELECT n.itemname, cn.itemname, f.itemname, a.level, div.divisionname,
       t.agenttype, l.itemname
FROM ccp.agtagents a
     INNER JOIN ccp.crpnpccorporations c ON a.corporationid = c.corporationid
     INNER JOIN ccp.crpnpcdivisions div ON a.divisionid = div.divisionid
     INNER JOIN ccp.invnames f ON c.factionid = f.itemid
     INNER JOIN ccp.invnames n ON a.agentid = n.itemid
     INNER JOIN ccp.invnames cn ON c.corporationid = cn.itemid
     INNER JOIN ccp.invnames l ON a.locationid = l.itemid
     INNER JOIN ccp.agtagenttypes t ON a.agenttypeid = t.agenttypeid
WHERE LOWER(n.itemname) = LOWER(%s)
""", (itemname,))
    if len(result) == 0:
        return None
    name, corpname, corpfaction, level, division, agenttype, loc = result[0]
    return {'type': 'agent',
            'name': name,
            'corporation': corpname,
            'corpfaction': corpfaction,
            'level': level,
            'division': division,
            'agenttype': agenttype,
            'location': loc}


def info_npccorp(db, itemname):
    result = db.execute("""
SELECT n.itemname, f.itemname
FROM ccp.crpnpccorporations c
       INNER JOIN ccp.invnames n
         ON c.corporationid = n.itemid
       INNER JOIN ccp.invnames f
         ON c.factionid = f.itemid
WHERE LOWER(n.itemname) = LOWER(%s)
""", (itemname,))
    if len(result) == 0:
        return None
    name, faction = result[0]
    return {'type': 'npccorp',
            'name': name,
            'faction': faction}


def info_faction(db, itemname):
    result = db.execute("""
SELECT factionname, factionid
FROM ccp.chrfactions
WHERE LOWER(factionname) = LOWER(%s)
""", (itemname,))
    if len(result) == 0:
        return None
    name, facid = result[0]
    info = {'type': 'faction',
            'name': name}
    result = db.execute("SELECT count(*) "
                        "FROM ccp.mapsolarsystems sys "
                        "     INNER JOIN ccp.mapconstellations const "
                        "       ON sys.constellationid = "
                        "          const.constellationid "
                        "     INNER JOIN ccp.mapregions r "
                        "       ON const.regionid = r.regionid "
                        "WHERE COALESCE(sys.factionid, const.factionid, "
                        "               r.factionid) = %s",
                        (facid,))
    info['numsystems'] = result[0][0]
    apiroot = api.root()
    fws = apiroot.map.FacWarSystems()
    numoccupied = 0
    numoccupiee = 0
    for row in fws.solarSystems:
        if row.owningFactionID == facid:
            if row.occupyingFactionID != 0:
                numoccupiee += 1
        if row.occupyingFactionID == facid:
            numoccupied += 1
    info['numoccupied'] = numoccupied
    info['numoccupiee'] = numoccupiee
    return info


def info_character(db, itemname):
    apiroot = api.root()
    try:
        names = apiroot.eve.CharacterID(names=itemname).characters
    except:
        return None
    if len(names) == 0 or names[0].characterID == 0:
        return None
    #name = names[0].name
    charid = names[0].characterID
    try:
        charinfo = apiroot.eve.CharacterInfo(characterID=charid)
    except api.eveapi.Error as e:
        if e.code not in (105,  # Invalid characterID
                          522): # Failed getting character information
            raise
        else:
            return None
    info = {'type': 'pilot',
            'name': charinfo.characterName,
            'race': charinfo.race,
            'bloodline': charinfo.bloodline,
            'corporation': charinfo.corporation,
            'alliance': getattr(charinfo, 'alliance', None),
            'security': charinfo.securityStatus,
            'corpticker': '',
            'allianceticker': '',
            'charstanding': 0,
            'corpstanding': 0,
            'allystanding': 0}
    corpinfo = apiroot.corp.CorporationSheet(
        corporationID=charinfo.corporationID)
    info['corpticker'] = corpinfo.ticker
    if getattr(charinfo, 'alliance', False):
        for ally in apiroot.eve.AllianceList().alliances:
            if ally.allianceID == charinfo.allianceID:
                info['allianceticker'] = ally.shortName
                break
    allykey = db.get_key('Gradient')
    for contact in allykey.corp.ContactList().allianceContactList:
        if charinfo.characterID == contact.contactID:
            info['charstanding'] = contact.standing
        elif charinfo.corporationID == contact.contactID:
            info['corpstanding'] = contact.standing
        elif getattr(charinfo, 'allianceID', None) == contact.contactID:
            info['allystanding'] = contact.standing
    # corp faction
    result = db.execute("SELECT f.name "
                        "FROM intel_corporation c "
                        "     INNER JOIN intel_faction f "
                        "       ON c.faction_id = f.id "
                        "WHERE c.corporationid = %s",
                        (charinfo.corporationID,))
    if len(result) > 0:
        info['militia'] = result[0][0]
    return info


def info_corporation(db, itemname):
    apiroot = api.root()
    names = apiroot.eve.CharacterID(names=itemname).characters
    if len(names) == 0 or names[0].characterID == 0:
        return None
    corpid = names[0].characterID
    try:
        corpinfo = apiroot.corp.CorporationSheet(
            corporationID=corpid)
    except api.eveapi.Error as e:
        if e.code == 522: # Failed getting character information
            raise
        else:
            return None
    info = {'type': 'corp',
            'name': corpinfo.corporationName,
            'ticker': corpinfo.ticker,
            'size': corpinfo.memberCount,
            'hq': corpinfo.stationName,
            'alliance': getattr(corpinfo, 'allianceName', ''),
            'faction': None,
            'corpstanding': 0,
            'allystanding': 0}
    if getattr(corpinfo, 'allianceID', 0) > 0:
        for ally in apiroot.eve.AllianceList().alliances:
            if ally.allianceID == corpinfo.allianceID:
                info['allianceticker'] = ally.shortName
                info['allysize'] = ally.memberCount
                break
    allykey = db.get_key('Gradient')
    for contact in allykey.corp.ContactList().allianceContactList:
        if corpinfo.corporationID == contact.contactID:
            info['corpstanding'] = contact.standing
        elif getattr(corpinfo, 'allianceID', None) == contact.contactID:
            info['allystanding'] = contact.standing
    # corp faction
    result = db.execute("SELECT f.name "
                        "FROM intel_corporation c "
                        "     INNER JOIN intel_faction f "
                        "       ON c.faction_id = f.id "
                        "WHERE c.corporationid = %s",
                        (corpinfo.corporationID,))
    if len(result) > 0:
        info['militia'] = result[0][0]
    return info


def info_alliance(db, itemname):
    apiroot = api.root()
    names = apiroot.eve.CharacterID(names=itemname).characters
    if len(names) == 0 or names[0].characterID == 0:
        return None
    allyid = names[0].characterID
    info = {'type': 'alliance'}
    membercorps = []
    for ally in apiroot.eve.AllianceList().alliances:
        if ally.allianceID == allyid:
            info['name'] = ally.name
            info['allianceticker'] = ally.shortName
            info['size'] = ally.memberCount
            info['allystanding'] = 0
            membercorps = [row.corporationID
                           for row in ally.memberCorporations]
            break
    if 'name' not in info:
        return None
    allykey = db.get_key('Gradient')
    for contact in allykey.corp.ContactList().allianceContactList:
        if allyid == contact.contactID:
            info['allystanding'] = contact.standing
    # corp faction
    result = db.execute("SELECT DISTINCT f.name "
                        "FROM intel_corporation c "
                        "     INNER JOIN intel_faction f "
                        "       ON c.faction_id = f.id "
                        "WHERE c.corporationid IN ({0})"
                        .format(", ".join(["%s"] * len(membercorps))),
                        membercorps)
    if len(result) == 1:
        info['militia'] = result[0][0]
    return info


WORMHOLEINFO = {
    u'A239': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 2000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 303,
              'wormholeTargetSystemClass': 8},
    u'A641': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 1000000000,
              'wormholeMaxStableMass': 2000000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 302,
              'wormholeTargetSystemClass': 7},
    u'A982': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 3000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 301,
              'wormholeTargetSystemClass': 6},
    u'B041': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 5000000000,
              'wormholeMaxStableTime': 2880,
              'wormholeTargetDistribution': 301,
              'wormholeTargetSystemClass': 6},
    u'B274': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 2000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 302,
              'wormholeTargetSystemClass': 7},
    u'B449': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 1000000000,
              'wormholeMaxStableMass': 2000000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 302,
              'wormholeTargetSystemClass': 7},
    u'B520': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 5000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 302,
              'wormholeTargetSystemClass': 7},
    u'C125': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 20000000,
              'wormholeMaxStableMass': 1000000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 297,
              'wormholeTargetSystemClass': 2},
    u'C140': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 1350000000,
              'wormholeMaxStableMass': 3000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 303,
              'wormholeTargetSystemClass': 8},
    u'C247': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 2000000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 298,
              'wormholeTargetSystemClass': 3},
    u'C248': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 1800000000,
              'wormholeMaxStableMass': 5000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 304,
              'wormholeTargetSystemClass': 9},
    u'C391': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 1800000000,
              'wormholeMaxStableMass': 5000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 303,
              'wormholeTargetSystemClass': 8},
    u'D364': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 1000000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 297,
              'wormholeTargetSystemClass': 2},
    u'D382': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 2000000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 297,
              'wormholeTargetSystemClass': 2},
    u'D792': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 1000000000,
              'wormholeMaxStableMass': 3000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 302,
              'wormholeTargetSystemClass': 7},
    u'D845': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 5000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 302,
              'wormholeTargetSystemClass': 7},
    u'E175': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 2000000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 299,
              'wormholeTargetSystemClass': 4},
    u'E545': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 2000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 304,
              'wormholeTargetSystemClass': 9},
    u'G024': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 2000000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 297,
              'wormholeTargetSystemClass': 2},
    u'H121': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 20000000,
              'wormholeMaxStableMass': 500000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 296,
              'wormholeTargetSystemClass': 1},
    u'H296': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 1350000000,
              'wormholeMaxStableMass': 3000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 300,
              'wormholeTargetSystemClass': 5},
    u'H900': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 3000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 300,
              'wormholeTargetSystemClass': 5},
    u'I182': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 2000000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 297,
              'wormholeTargetSystemClass': 2},
    u'J244': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 20000000,
              'wormholeMaxStableMass': 1000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 303,
              'wormholeTargetSystemClass': 8},
    u'K329': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 1800000000,
              'wormholeMaxStableMass': 5000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 304,
              'wormholeTargetSystemClass': 9},
    u'K346': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 3000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 304,
              'wormholeTargetSystemClass': 9},
    u'L477': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 2000000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 298,
              'wormholeTargetSystemClass': 3},
    u'L614': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 20000000,
              'wormholeMaxStableMass': 1000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 300,
              'wormholeTargetSystemClass': 5},
    u'M267': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 1000000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 298,
              'wormholeTargetSystemClass': 3},
    u'M555': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 1000000000,
              'wormholeMaxStableMass': 3000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 300,
              'wormholeTargetSystemClass': 5},
    u'M609': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 20000000,
              'wormholeMaxStableMass': 1000000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 299,
              'wormholeTargetSystemClass': 4},
    u'N062': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 3000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 300,
              'wormholeTargetSystemClass': 5},
    u'N110': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 20000000,
              'wormholeMaxStableMass': 1000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 302,
              'wormholeTargetSystemClass': 7},
    u'N290': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 1350000000,
              'wormholeMaxStableMass': 3000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 303,
              'wormholeTargetSystemClass': 8},
    u'N432': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 1350000000,
              'wormholeMaxStableMass': 3000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 300,
              'wormholeTargetSystemClass': 5},
    u'N766': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 2000000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 297,
              'wormholeTargetSystemClass': 2},
    u'N770': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 3000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 300,
              'wormholeTargetSystemClass': 5},
    u'N944': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 1350000000,
              'wormholeMaxStableMass': 3000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 303,
              'wormholeTargetSystemClass': 8},
    u'N968': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 2000000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 298,
              'wormholeTargetSystemClass': 3},
    u'O128': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 1000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 299,
              'wormholeTargetSystemClass': 4},
    u'O477': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 2000000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 298,
              'wormholeTargetSystemClass': 3},
    u'O883': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 20000000,
              'wormholeMaxStableMass': 1000000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 298,
              'wormholeTargetSystemClass': 3},
    u'P060': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 20000000,
              'wormholeMaxStableMass': 500000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 296,
              'wormholeTargetSystemClass': 1},
    u'Q317': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 20000000,
              'wormholeMaxStableMass': 500000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 296,
              'wormholeTargetSystemClass': 1},
    u'R051': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 1000000000,
              'wormholeMaxStableMass': 3000000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 303,
              'wormholeTargetSystemClass': 8},
    u'R474': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 3000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 301,
              'wormholeTargetSystemClass': 6},
    u'R943': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 750000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 297,
              'wormholeTargetSystemClass': 2},
    u'S047': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 3000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 302,
              'wormholeTargetSystemClass': 7},
    u'S199': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 1350000000,
              'wormholeMaxStableMass': 3000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 304,
              'wormholeTargetSystemClass': 9},
    u'S804': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 20000000,
              'wormholeMaxStableMass': 1000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 301,
              'wormholeTargetSystemClass': 6},
    u'T405': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 2000000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 299,
              'wormholeTargetSystemClass': 4},
    u'U210': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 3000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 303,
              'wormholeTargetSystemClass': 8},
    u'U319': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 1350000000,
              'wormholeMaxStableMass': 3000000000,
              'wormholeMaxStableTime': 2880,
              'wormholeTargetDistribution': 301,
              'wormholeTargetSystemClass': 6},
    u'U574': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 3000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 301,
              'wormholeTargetSystemClass': 6},
    u'V283': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 1000000000,
              'wormholeMaxStableMass': 3000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 304,
              'wormholeTargetSystemClass': 9},
    u'V301': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 20000000,
              'wormholeMaxStableMass': 500000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 296,
              'wormholeTargetSystemClass': 1},
    u'V753': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 1350000000,
              'wormholeMaxStableMass': 3000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 301,
              'wormholeTargetSystemClass': 6},
    u'V911': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 1350000000,
              'wormholeMaxStableMass': 3000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 300,
              'wormholeTargetSystemClass': 5},
    u'W237': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 1350000000,
              'wormholeMaxStableMass': 3000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 301,
              'wormholeTargetSystemClass': 6},
    u'X702': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 1000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 298,
              'wormholeTargetSystemClass': 3},
    u'X877': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 2000000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 299,
              'wormholeTargetSystemClass': 4},
    u'Y683': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 2000000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 299,
              'wormholeTargetSystemClass': 4},
    u'Y790': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 20000000,
              'wormholeMaxStableMass': 500000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 296,
              'wormholeTargetSystemClass': 1},
    u'Z060': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 20000000,
              'wormholeMaxStableMass': 1000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 304,
              'wormholeTargetSystemClass': 9},
    u'Z142': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 1350000000,
              'wormholeMaxStableMass': 3000000000,
              'wormholeMaxStableTime': 1440,
              'wormholeTargetDistribution': 304,
              'wormholeTargetSystemClass': 9},
    u'Z457': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 300000000,
              'wormholeMaxStableMass': 2000000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 299,
              'wormholeTargetSystemClass': 4},
    u'Z647': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 20000000,
              'wormholeMaxStableMass': 500000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 296,
              'wormholeTargetSystemClass': 1},
    u'Z971': {'wormholeMassRegeneration': 0,
              'wormholeMaxJumpMass': 20000000,
              'wormholeMaxStableMass': 100000000,
              'wormholeMaxStableTime': 960,
              'wormholeTargetDistribution': 296,
              'wormholeTargetSystemClass': 1}
    }

WHCLASSDESC = {
    1: "unknown space",
    2: "unknown space",
    3: "unknown space",
    4: "dangerous space",
    5: "deadly space",
    6: "deadly space",
    7: "high-sec",
    8: "low-sec",
    9: "zero-sec",
    }
