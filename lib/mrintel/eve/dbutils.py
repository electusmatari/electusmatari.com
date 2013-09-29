import ConfigParser
import datetime
import psycopg2

from mrintel.eve import api


class DBConnection(object):
    def __init__(self):
        conf = ConfigParser.SafeConfigParser()
        conf.read(["/home/forcer/Projects/private/mrintel.conf"])
        self.conn = psycopg2.connect(host=conf.get('database', 'host'),
                                     user=conf.get('database', 'user'),
                                     password=conf.get('database', 'password'),
                                     database=conf.get('database', 'database'))
        self.jumps = None

    def execute(self, fmt, args=()):
        c = self.conn.cursor()
        c.execute(fmt, args)
        return c.fetchall()

    def find_type(self, needle):
        c = self.conn.cursor()
        c.execute("SELECT typename, typeid FROM ccp.invtypes "
                  "WHERE LOWER(typename) = LOWER(%s)", (needle,))
        if c.rowcount == 1:
            return c.fetchone()
        c.execute("SELECT typename, typeid FROM ccp.invtypes "
                  "WHERE typename ILIKE %s", ("%" + needle + "%",))
        if c.rowcount == 1:
            return c.fetchone()
        else:
            return ([typename for (typename, typeid) in c.fetchall()],
                    None)

    def get_typename(self, typeid):
        c = self.conn.cursor()
        c.execute("SELECT typename FROM ccp.invtypes "
                  "WHERE typeid = %s", (typeid,))
        if c.rowcount > 0:
            return c.fetchone()[0]
        else:
            return "<typeID {0}>".format(typeid)

    def get_itemname(self, itemid):
        c = self.conn.cursor()
        c.execute("SELECT itemname FROM ccp.invnames "
                  "WHERE itemid = %s", (itemid,))
        if c.rowcount > 0:
            return c.fetchone()[0]
        apiroot = api.root()
        try:
            names = apiroot.eve.CharacterName(ids=itemid)
        except api.eveapi.Error as e:
            if e.code != 130:
                raise
            else:
                return "<itemID {0}>".format(itemid)
        else:
            return names.characters[0].name

    def sold_by_npccorps(self, typeid):
        c = self.conn.cursor()
        c.execute("SELECT n.itemname "
                  "FROM ccp.crpnpccorporationtrades t "
                  "     INNER JOIN ccp.invnames n "
                  "       ON t.corporationid = n.itemid "
                  "WHERE typeid = %s",
                  (typeid,))
        return [corpname for (corpname,) in c.fetchall()]

    def baseprice(self, typeid):
        c = self.conn.cursor()
        c.execute("SELECT baseprice "
                  "FROM ccp.invtypes "
                  "WHERE typeid = %s",
                  (typeid,))
        return float(c.fetchone()[0])

    def marketgroup(self, typeid):
        c = self.conn.cursor()
        c.execute("SELECT marketgroupid "
                  "FROM ccp.invtypes "
                  "WHERE typeid = %s",
                  (typeid,))
        return c.fetchone()[0]

    def itemname(self, itemid):
        c = self.conn.cursor()
        c.execute("SELECT itemname "
                  "FROM ccp.invnames "
                  "WHERE itemid = %s",
                  (itemid,))
        return c.fetchone()[0]

    def stationid2systemname(self, stationid):
        c = self.conn.cursor()
        c.execute("SELECT sys.solarsystemname "
                  "FROM ccp.stastations st "
                  "     INNER JOIN ccp.mapsolarsystems sys "
                  "       ON st.solarsystemid = sys.solarsystemid "
                  "WHERE st.stationid = %s",
                  (stationid,))
        return c.fetchone()[0]

    def distance(self, sysid1, sysid2):
        if self.jumps is None:
            c = self.conn.cursor()
            c.execute("SELECT fromsolarsystemid, tosolarsystemid "
                      "FROM ccp.mapsolarsystemjumps")
            self.jumps = {}
            for fromsysid, tosysid in c.fetchall():
                self.jumps.setdefault(fromsysid, [])
                self.jumps[fromsysid].append(tosysid)
        agenda = [(sysid1, 0)]
        visited = set()
        while agenda:
            sysid, distance = agenda.pop(0)
            if sysid == sysid2:
                return distance
            if sysid in visited:
                continue
            visited.add(sysid)
            agenda.extend((nextsysid, distance + 1)
                          for nextsysid in self.jumps[sysid])
        return -1

    def pricecheck(self, typeid, sethours=360, regionlimit=None):
        c = self.conn.cursor()
        sql = ("SELECT o.price, o.volremaining, o.regionid, "
               "       o.solarsystemid, o.stationid, u.cachetimestamp "
               "FROM uploader_marketorder o "
               "     INNER JOIN uploader_upload u "
               "       ON o.upload_id = u.id "
               "WHERE o.typeid = %s "
               "  AND NOT o.bid "
               "  AND u.cachetimestamp > NOW() - "
               "                         INTERVAL '{sethours} hours' ")
        args = [typeid]
        if regionlimit is not None:
            sql += "  AND o.regionid IN ({regionfmt})"
            args.extend(regionlimit)
        c.execute(sql.format(sethours=int(sethours),
                             regionfmt=", ".join(["%s"] * len(regionlimit))),
                  args)
        for (price, volremain, regionid, solarsystemid, stationid,
             cachetimestamp) in c.fetchall():
            yield {'price': price,
                   'quantity': volremain,
                   'regionid': regionid,
                   'solarsystemid': solarsystemid,
                   'stationid': stationid,
                   'checked': cachetimestamp}

    def get_key(self, name):
        c = self.conn.cursor()
        c.execute("SELECT keyid, vcode, characterid "
                  "FROM ccpeve_apikey WHERE name = %s", (name,))
        keyid, vcode, charid = c.fetchone()
        key = api.root().auth(keyID=keyid,
                              vCode=vcode)
        if charid is not None:
            key = key.character(charid)
            key._path = ''
        return key

    def update_tracked_entities(self):
        """
        Mark all tracked entities as to be checked.
        """
        allyids = set()
        corpids = set()
        charids = set()
        c = self.conn.cursor()
        c.execute("""
SELECT ally.allianceid
FROM intel_trackedentity tr
     INNER JOIN intel_alliance ally
       ON tr.alliance_id = ally.id
""")
        allyids.update(allyid for (allyid,) in c.fetchall())
        c.execute("""
SELECT corp.corporationid
FROM intel_trackedentity tr
     INNER JOIN intel_alliance ally
       ON tr.alliance_id = ally.id
     INNER JOIN intel_corporation corp
       ON corp.alliance_id = ally.id
""")
        corpids.update(corpid for (corpid,) in c.fetchall())
        c.execute("""
SELECT char.characterid
FROM intel_trackedentity tr
     INNER JOIN intel_alliance ally
       ON tr.alliance_id = ally.id
     INNER JOIN intel_corporation corp
       ON corp.alliance_id = ally.id
     INNER JOIN intel_pilot char
       ON corp.id = char.corporation_id
""")
        charids.update(charid for (charid,) in c.fetchall())
        c.execute("""
SELECT corp.corporationid
FROM intel_trackedentity tr
     INNER JOIN intel_corporation corp
       ON tr.corporation_id = corp.id
""")
        corpids.update(corpid for (corpid,) in c.fetchall())
        c.execute("""
SELECT char.characterid
FROM intel_trackedentity tr
     INNER JOIN intel_corporation corp
       ON tr.corporation_id = corp.id
     INNER JOIN intel_pilot char
       ON corp.id = char.corporation_id
""")
        charids.update(charid for (charid,) in c.fetchall())
        self.mark_chars_for_api(charids)
        self.mark_corps_for_api(charids)
        self.mark_alliances_for_api(allyids)

    def update_facwar_entities(self):
        c = self.conn.cursor()
        c.execute("UPDATE intel_corporation "
                  "SET do_api_check = true "
                  "WHERE faction_id IS NOT NULL")
        self.conn.commit()

    def mark_chars_for_api(self, charidseq):
        c = self.conn.cursor()
        c.execute("UPDATE intel_pilot "
                  "SET do_api_check = true "
                  "WHERE characterid IN ({0})"
                  .format(", ".join(["%s"] * len(charidseq))),
                  list(charidseq))
        self.conn.commit()

    def mark_corps_for_api(self, corpidseq):
        c = self.conn.cursor()
        c.execute("UPDATE intel_corporation "
                  "SET do_api_check = true "
                  "WHERE corporationid IN ({0})"
                  .format(", ".join(["%s"] * len(corpidseq))),
                  list(corpidseq))
        self.conn.commit()

    def mark_corps_for_cache(self, corpidseq):
        c = self.conn.cursor()
        c.execute("UPDATE intel_corporation "
                  "SET do_cache_check = true "
                  "WHERE corporationid IN ({0})"
                  .format(", ".join(["%s"] * len(corpidseq))),
                  list(corpidseq))
        self.conn.commit()

    def mark_alliances_for_api(self, allyidseq):
        c = self.conn.cursor()
        c.execute("UPDATE intel_alliance "
                  "SET do_api_check = true "
                  "WHERE allianceid IN ({0})"
                  .format(", ".join(["%s"] * len(allyidseq))),
                  list(allyidseq))
        self.conn.commit()

    def guess_itemtype(self, itemid):
        """
        Guess the itemtype of the given itemID.

        One of "character", "corporation" or "alliance".
        """
        c = self.conn.cursor()
        c.execute("SELECT characterid FROM intel_pilot "
                  "WHERE characterid = %s", (itemid,))
        if c.rowcount > 0:
            return "character"
        c.execute("SELECT corporationid FROM intel_corporation "
                  "WHERE corporationid = %s", (itemid,))
        if c.rowcount > 0:
            return "corporation"
        c.execute("SELECT allianceid FROM intel_alliance "
                  "WHERE allianceid = %s", (itemid,))
        if c.rowcount > 0:
            return "alliance"
        # Not in DB. We have to do some guesswork from the API.
        apiroot = api.root()
        try:
            apiroot.eve.CharacterInfo(characterID=itemid)
            return "character"
        except api.eveapi.Error as e:
            if e.code not in (105,  # Invalid characterID
                              522): # Failed getting character information
                raise
        try:
            apiroot.corp.CorporationSheet(corporationID=itemid)
            return "corporation"
        except api.eveapi.Error as e:
            if e.code != 523: # Failed getting corporation information
                raise
        # Otherwise, must be alliance ...
        return "alliance"

    def get_api_characters(self):
        """
        Return a list of characterIDs that should be updated.
        """
        c = self.conn.cursor()
        c.execute("SELECT characterid "
                  "FROM intel_pilot "
                  "WHERE do_api_check OR lastapi IS NULL")
        return [charid for (charid,) in c.fetchall()]

    def get_api_corporations(self):
        """
        Return a list of characterIDs that should be updated.
        """
        c = self.conn.cursor()
        c.execute("SELECT corporationid "
                  "FROM intel_corporation "
                  "WHERE do_api_check OR lastapi IS NULL")
        return [corpid for (corpid,) in c.fetchall()]

    def get_api_alliances(self):
        """
        Return a list of characterIDs that should be updated.
        """
        c = self.conn.cursor()
        c.execute("SELECT allianceid "
                  "FROM intel_alliance "
                  "WHERE do_api_check OR lastapi IS NULL")
        return [allyid for (allyid,) in c.fetchall()]

    def ensure_character_exists(self, characterid):
        c = self.conn.cursor()
        self.conn.commit()
        try:
            c.execute("INSERT INTO intel_pilot (name, characterid, lastseen) "
                      "VALUES ('', %s, %s)",
                      (characterid, datetime.datetime.utcnow()))
            self.conn.commit()
        except:
            self.conn.rollback()

    def ensure_corporation_exists(self, corporationid):
        c = self.conn.cursor()
        self.conn.commit()
        try:
            c.execute("INSERT INTO intel_corporation (name, corporationid, "
                      "  lastseen) "
                      "VALUES ('', %s, %s)",
                      (corporationid, datetime.datetime.utcnow()))
            self.conn.commit()
        except:
            self.conn.rollback()

    def ensure_alliance_exists(self, allianceid):
        c = self.conn.cursor()
        self.conn.commit()
        try:
            c.execute("INSERT INTO intel_alliance (name, allianceid, "
                      "  lastseen) "
                      "VALUES ('', %s, %s)",
                      (allianceid, datetime.datetime.utcnow()))
            self.conn.commit()
        except:
            self.conn.rollback()

    # Monster of a method!
    def update_generic(self, itemid, kwargs, table, idfield, dbidfield,
                       allowed_fields):
        c = self.conn.cursor()
        names = []
        values = []
        for k, v in kwargs.items():
            if k == 'characterid':
                k = "pilot_id"
                if v is not None:
                    self.ensure_character_exists(v)
                    c.execute("SELECT id FROM intel_pilot "
                              "WHERE characterid = %s", (v,))
                    v = c.fetchone()[0]
            elif k == 'corporationid':
                k = "corporation_id"
                if v is not None:
                    self.ensure_corporation_exists(v)
                    c.execute("SELECT id FROM intel_corporation "
                              "WHERE corporationid = %s", (v,))
                    v = c.fetchone()[0]
            elif k == 'allianceid':
                k = "alliance_id"
                if v is not None:
                    self.ensure_alliance_exists(v)
                    c.execute("SELECT id FROM intel_alliance "
                              "WHERE allianceid = %s", (v,))
                    v = c.fetchone()[0]
            elif k == 'factionid':
                k = "faction_id"
                if v is not None:
                    c.execute("SELECT id FROM intel_faction "
                              "WHERE factionid = %s", (v,))
                    v = c.fetchone()[0]
            if k in allowed_fields:
                names.append(k)
                values.append(v)
        # Get old values and update any changes
        c.execute("SELECT id FROM {table} WHERE {idfield} = %s"
                  .format(table=table, idfield=idfield),
                  (itemid,))
        dbid = c.fetchone()[0]
        c.execute("SELECT {names} FROM {table} WHERE {idfield} = %s"
                  .format(names=", ".join(names),
                          table=table,
                          idfield=idfield),
                  (itemid,))
        old_values = c.fetchone()
        for name, old, new in zip(names, old_values, values):
            if name == 'faction_id':
                if old == new:
                    continue
                c.execute("INSERT INTO intel_change (timestamp, changetype, "
                          "  {dbidfield}, oldstring, newstring, "
                          "  oldfaction_id, newfaction_id) "
                          "VALUES (%s, %s, %s, '', '', %s, %s)"
                          .format(dbidfield=dbidfield),
                          (datetime.datetime.utcnow(),
                           'faction', dbid, old, new))
            elif name == 'alliance_id':
                if old == new:
                    continue
                c.execute("INSERT INTO intel_change (timestamp, changetype, "
                          "  {dbidfield}, oldstring, newstring, "
                          "  oldalliance_id, newalliance_id) "
                          "VALUES (%s, %s, %s, '', '', %s, %s)"
                          .format(dbidfield=dbidfield),
                          (datetime.datetime.utcnow(),
                           'alliance', dbid, old, new))
            elif name == 'corporation_id':
                if old == new:
                    continue
                c.execute("INSERT INTO intel_change (timestamp, changetype, "
                          "  {dbidfield}, oldstring, newstring, "
                          "  oldcorp_id, newcorp_id) "
                          "VALUES (%s, %s, %s, '', '', %s, %s)"
                          .format(dbidfield=dbidfield),
                          (datetime.datetime.utcnow(),
                           'corporation', dbid, old, new))
            elif name == 'name':
                if old == new:
                    continue
                c.execute("INSERT INTO intel_change (timestamp, changetype, "
                          "  {dbidfield}, oldstring, newstring) "
                          "VALUES (%s, %s, %s, %s, %s)"
                          .format(dbidfield=dbidfield),
                          (datetime.datetime.utcnow(),
                           'name', dbid, old, new))
            elif name == 'members':
                if old == new:
                    continue
                c.execute("INSERT INTO intel_change (timestamp, changetype, "
                          "  {dbidfield}, oldstring, newstring, "
                          "  oldint, newint) "
                          "VALUES (%s, %s, %s, '', '', %s, %s)"
                          .format(dbidfield=dbidfield),
                          (datetime.datetime.utcnow(),
                           'name', dbid, old, new))
        c.execute("UPDATE {table} "
                  "SET {names} WHERE {idfield} = %s"
                  .format(table=table,
                          idfield=idfield,
                          names=", ".join("{0} = %s".format(name)
                                          for name in names)),
                  values + [itemid])
        self.conn.commit()

    def update_character(self, characterid, **kwargs):
        self.update_generic(characterid, kwargs,
                            'intel_pilot', 'characterid', 'pilot_id',
                            ["name", "corporation_id", "alliance_id",
                             "lastseen", "security", "lastkillinfo",
                             "lastapi", "lastcache", "evewho",
                             "do_api_check"])

    def update_corporation(self, corporationid, **kwargs):
        self.update_generic(corporationid, kwargs,
                            'intel_corporation', 'corporationid',
                            'corporation_id',
                            ["name", "alliance_id", "faction_id",
                             "lastseen", "ticker", "members", "standing",
                             "lastkillinfo", "lastapi", "lastcache",
                             "do_api_check", "do_cache_check"])

    def update_alliance(self, allianceid, **kwargs):
        self.update_generic(allianceid, kwargs,
                            'intel_alliance', 'allianceid', 'alliance_id',
                            ["name", "lastseen", "ticker", "members",
                             "standing", "lastkillinfo", "lastapi",
                             "lastcache", "do_api_check"])

    def get_interesting_systems_for_hot(self):
        c = self.conn.cursor()
        c.execute("SELECT sys.solarsystemid, sys.solarsystemname "
                  "FROM ccp.mapsolarsystems sys "
                  "     INNER JOIN ccp.mapregions r "
                  "       ON sys.regionid = r.regionid "
                  "     LEFT JOIN ccp.warcombatzonesystems w "
                  "       ON sys.solarsystemid = w.solarsystemid "
                  "WHERE "
                  "  (r.regionname IN ('Heimatar', 'Metropolis', "
                  "                    'Molden Heath') "
                  "   AND sys.security < 0.45) "
                  "  OR "
                  "  (r.regionname IN ('Devoid', 'The Bleak Lands') "
                  "   AND w.combatzoneid = 3)")
        return dict(c.fetchall())
