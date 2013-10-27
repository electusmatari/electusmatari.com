import datetime
import logging
import threading
import time

from mrintel.eve import api
from mrintel.eve import dbutils

ONE_DAY_SECONDS = 24 * 60 * 60


class APICheck(threading.Thread):
    def __init__(self, bot):
        super(APICheck, self).__init__()
        self.daemon = True
        self.bot = bot
        self.api = None
        self.conn = None
        self.last_daily_run = time.time()

    def run(self):
        self.conn = dbutils.DBConnection()
        self.api = api.root()
        self.emapi = self.conn.get_key('Gradient')
        while True:
            try:
                self.run2()
            except:
                logging.exception("Exception during APICheck.run()")
                time.sleep(5 * 60)

    def run2(self):
        while True:
            now = time.time()
            if self.last_daily_run < now - ONE_DAY_SECONDS:
                self.last_daily_run = now
                self.once_a_day()
            self.once_a_minute()
            time.sleep(60)

    def once_a_minute(self):
        self.do_api_check()

    def once_a_day(self):
        self.get_facwartopstats_ids()
        self.update_standings()
        self.conn.update_tracked_entities()
        self.conn.update_facwar_entities()

    def get_facwartopstats_ids(self):
        """
        Get new characters and corporations from FacWarTopStats.
        """
        fwts = self.api.eve.FacWarTopStats()
        charids = set()
        corpids = set()
        for list_ in ['KillsYesterday', 'KillsLastWeek', 'KillsTotal',
                      'VictoryPointsYesterday', 'VictoryPointsLastWeek',
                      'VictoryPointsTotal']:
            for row in getattr(fwts.characters, list_):
                charids.add(row.characterID)
            for row in getattr(fwts.corporations, list_):
                corpids.add(row.corporationID)
        for charid in charids:
            self.conn.ensure_character_exists(charid)
        self.conn.mark_chars_for_api(charids)
        for corpid in corpids:
            self.conn.ensure_corporation_exists(corpid)
        self.conn.mark_corps_for_api(corpids)
        self.conn.mark_corps_for_cache(corpids)

    def update_standings(self):
        """
        Update alliance standings in the database.

        Also add new corporations and alliances that way.
        """
        cl = self.emapi.corp.ContactList()
        for contact in cl.allianceContactList:
            try:
                contacttype = self.conn.guess_itemtype(contact.contactID)
            except RuntimeError:  # 500 Internal Server Error
                logging.exception("Exception checking contact {0}"
                                  .format(contact.contactID))
                continue
            if contacttype == 'character':
                self.conn.ensure_character_exists(contact.contactID)
            elif contacttype == 'corporation':
                self.conn.ensure_corporation_exists(contact.contactID)
                self.conn.update_corporation(contact.contactID,
                                             standing=contact.standing)
            elif contacttype == 'alliance':
                self.conn.ensure_alliance_exists(contact.contactID)
                self.conn.update_alliance(contact.contactID,
                                          standing=contact.standing)

    def do_api_check(self):
        """
        Update all entities that have never been checked on the API,
        or where do_api_check is true.
        """
        for charid in self.conn.get_api_characters():
            self.update_character(charid)
        for corpid in self.conn.get_api_corporations():
            self.update_corporation(corpid)
        for allyid in self.conn.get_api_alliances():
            self.update_alliance(allyid)

    def update_character(self, charid):
        if charid == 0:
            return
        try:
            charinfo = self.api.eve.CharacterInfo(characterID=charid)
        except:
            logging.error("Error updating character {0}".format(charid))
            raise
        self.conn.update_character(charid,
                                   name=charinfo.characterName,
                                   corporationid=charinfo.corporationID,
                                   allianceid=getattr(charinfo, 'allianceID',
                                                      None),
                                   security=charinfo.securityStatus,
                                   do_api_check=False,
                                   lastseen=datetime.datetime.utcnow(),
                                   lastapi=datetime.datetime.utcnow())

    def update_corporation(self, corpid):
        if corpid == 0:
            return
        try:
            corpinfo = self.api.corp.CorporationSheet(corporationID=corpid)
        except api.eveapi.Error as e:
            if e.code == 523:
                # Failed to get corp info. No idea where those are
                # coming from.
                self.conn.update_corporation(
                    corpid,
                    name="*Invalid*",
                    allianceid=None,
                    ticker="",
                    members=0,
                    do_api_check=False,
                    lastseen=datetime.datetime.utcnow(),
                    lastapi=datetime.datetime.utcnow())
                return
            else:
                logging.error("Error updating corporation {0}".format(corpid))
                raise
        except:
            logging.error("Error updating corporation {0}".format(corpid))
            raise
        self.conn.update_corporation(corpid,
                                     name=corpinfo.corporationName,
                                     allianceid=corpinfo.allianceID or None,
                                     ticker=corpinfo.ticker,
                                     members=corpinfo.memberCount,
                                     do_api_check=False,
                                     lastseen=datetime.datetime.utcnow(),
                                     lastapi=datetime.datetime.utcnow())

    def update_alliance(self, allyid):
        for ally in self.api.eve.AllianceList().alliances:
            if ally.allianceID == allyid:
                self.conn.update_alliance(allyid,
                                          name=ally.name,
                                          ticker=ally.shortName,
                                          members=ally.memberCount,
                                          do_api_check=False,
                                          lastseen=datetime.datetime.utcnow(),
                                          lastapi=datetime.datetime.utcnow())
                return
        self.conn.update_alliance(allyid,
                                  members=0,
                                  do_api_check=False,
                                  lastapi=datetime.datetime.utcnow())
