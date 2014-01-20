import datetime
import logging
import threading
import time

from mrintel.eve import dbutils

NOTIFICATION_CACHE_TIME = datetime.timedelta(days=7)

##################################################################
# Calendar events

# event.eventText.replace("<br />", "\n")
"""<b>Minmatar Control Tower Medium</b> will run out of fuel and go
offline.

<b>Name</b>: <structure name>
<b>Location</b>: Heimatar / Evannater / Gusandall
<b>Moon</b>: Gusandall VII - Moon 1
<b>Fuel bay capacity</b>: 70000.0 m<sup>3</sup>

Resources in fuel bay when control tower runs out:
<ul><li><b>Minmatar Fuel Block</b>: 0 unit(s)
</li></ul>"""

class CalendarWatcher(threading.Thread):
    def __init__(self, bot):
        super(CalendarWatcher, self).__init__()
        self.daemon = True
        self.bot = bot
        conn = dbutils.DBConnection()
        self.api = conn.get_key('Notifications')

    def run(self):
        while True:
            try:
                self.run2()
            except:
                logging.exception("Exception during CalendarWatcher.run()")
            time.sleep(60 * 5)

    def run2(self):
        while True:
            if not self.bot.is_registered:
                time.sleep(15)
                continue
            apiresult = self.api.char.UpcomingCalendarEvents()
            for event in apiresult.upcomingEvents:
                if self.is_interesting(event):
                    self.notify(event)
            time.sleep(60 * 60)

    def is_interesting(self, event):
        now = time.time()
        if not (0 < (event.eventDate - now) < 60 * 24):
            return False
        if event.ownerName != 'Gradient':
            return False
        if 'run out of fuel' not in event.eventText:
            return False
        return True

    def notify(self, event):
        hours = int((event.eventDate - time.time()) / 60 / 60)
        # match = re.search("<b>Moon</b>: (.*?)<br />", event.eventText)
        # if match is not None:
        #     text = "Control tower at " + match.group(1)
        # else:
        #     text = event.eventTitle
        text = ("[POS] A tower is meeping ({0} hours left)"
                .format(hours))
        self.bot.msg("#grd", text)


##################################################################
# Notifications

class NotificationWatcher(threading.Thread):
    def __init__(self, bot):
        super(NotificationWatcher, self).__init__()
        self.daemon = True
        self.bot = bot
        self.db = dbutils.DBConnection()
        self.api = self.db.get_key('Notifications')
        self.known = None

    def run(self):
        while True:
            try:
                self.run2()
            except:
                logging.exception("Exception during NotificationWatcher.run()")
            time.sleep(60 * 5)

    def run2(self):
        while True:
            if self.known is None:
                first_run = True
                self.known = {}
            else:
                first_run = False
            nlist = self.api.char.Notifications()
            for row in nlist.notifications:
                if row.notificationID not in self.known:
                    timestamp = datetime.datetime.utcfromtimestamp(
                        row.sentDate)
                    if not first_run:
                        self.notify(timestamp, row.typeID, row.notificationID)
                    self.known[row.notificationID] = timestamp
            for notificationID, timestamp in self.known.items():
                delta = timestamp - datetime.datetime.utcnow()
                if delta > NOTIFICATION_CACHE_TIME:
                    del self.known[notificationID]
            time.sleep(nlist._meta.cachedUntil - nlist._meta.currentTime)

    def notify(self, timestamp, typeid, notificationid):
        ntext = self.api.char.NotificationTexts(ids=notificationid
                                                ).notifications[0]
        handler = getattr(self, "notify_{0}".format(typeid), None)
        if handler is None:
            return
        data = ntext.data
        fields = dict([field.strip() for field in row.split(":")]
                      for row in data.split("\n") if ":" in row)
        self.resolve_fields(fields)
        handler(timestamp, fields)

    def notify_channel(self, channel, text):
        self.bot.msg(channel, text)

    def resolve_fields(self, fields):
        new = {}
        for k, v in fields.items():
            if k in ['aggressorAllianceID', 'aggressorCorpID', 'aggressorID',
                     'moonID', 'solarSystemID', 'planetID', 'againstID',
                     'declaredByID']:
                new[k.rstrip("ID")] = self.db.get_itemname(v)
            elif k in ['typeID', 'planetTypeID']:
                new[k.rstrip("ID")] = self.db.get_typename(v)
        fields.update(new)

    def notify_75(self, timestamp, fields):
        # 75: Tower Alert
        # aggressorAllianceID: 1307452790
        # aggressorCorpID: 696599088
        # aggressorID: 1674193534
        # armorValue: 1.0
        # hullValue: 1.0
        # moonID: 40162621
        # shieldValue: 0.46
        # solarSystemID: 30002556
        # typeID: 17181
        s = "[Tower Alert] {aggressor} of {aggressorCorp}".format(**fields)
        if ('aggressorAllianceID' in fields and
            fields['aggressorAllianceID'] > 0
            ):
            s += ", {aggressorAlliance}".format(**fields)
        s += " aggressed {type} on {moon}.".format(**fields)
        self.notify_channel("#grd", s)

    def notify_76(self, timestamp, fields):
        # 76: Tower Resource Alert
        pass

    def notify_93(self, timestamp, fields):
        # 93: Customs office has been attacked
        # aggressorAllianceID: 491350469
        # aggressorCorpID: 1884902606
        # aggressorID: 90105966
        # planetID: 40131348
        # planetTypeID: 2063
        # shieldLevel: 0.9895652238797727
        # solarSystemID: 30002059
        # typeID: 2233
        s = ("[Customs Office Alert] {aggressor} of {aggressorCorp}"
             .format(**fields))
        if ('aggressorAllianceID' in fields and
            fields['aggressorAllianceID'] > 0
            ):
            s += ", {aggressorAlliance}".format(**fields)
        s += " aggressed {type} on {planet}.".format(**fields)
        self.notify_channel("#grd", s)

    def notify_94(self, timestamp, fields):
        # 94: Customs Office has entered reinforced
        # aggressorAllianceID: 491350469
        # aggressorCorpID: 1323105611
        # aggressorID: 1910163461
        # planetID: 40131348
        # planetTypeID: 2063
        # reinforceExitTime: 129703536720000000
        # solarSystemID: 30002059
        # typeID: 2233
        s = ("[Customs Office Reinforced] {aggressor} of {aggressorCorp}"
             .format(**fields))
        if ('aggressorAllianceID' in fields and
            fields['aggressorAllianceID'] > 0
            ):
            s += ", {aggressorAlliance}".format(**fields)
        s += " reinforced {type} on {planet}.".format(**fields)
        reinf = wintime_to_datetime(long(fields['reinforceExitTime']))
        s += (" Will come out of reinforce on {0}."
              .format(reinf.strftime("%Y-%m-%d %H:%M:%S")))
        self.notify_channel("#grd", s)

    def notify_5(self, timestamp, fields):
        # 5: notificationTypeAllWarDeclaredMsg
        # againstID: 1700517403
        # cost: 100000000
        # declaredByID: 701459600
        # delayHours: 24
        # hostileState: 0
        s = ("[War] {declaredBy} has declared war on {against}."
             .format(**fields))
        self.notify_channel("#grd", s)

    def notify_27(self, timestamp, fields):
        # 27: notificationTypeCorpWarDeclaredMsg
        s = ("[War] {declaredBy} has declared war on {against}."
             .format(**fields))
        self.notify_channel("#grd", s)

    def notify_28(self, timestamp, fields):
        # 28: notificationTypeCorpWarFightingLegalMsg
        s = ("[War] {declaredBy} has declared war on {against}."
             .format(**fields))
        self.notify_channel("#grd", s)

    def notify_6(self, timestamp, fields):
        # 6: notificationTypeAllWarSurrenderMsg
        # againstID: 98079470
        # cost: 100000000
        # declaredByID: 701459600
        # delayHours: -53
        # hostileState: 1
        s = ("[War] {against} has surrendered to {declaredBy}."
             .format(**fields))
        self.notify_channel("#grd", s)

    def notify_29(self, timestamp, fields):
        # 29: notificationTypeCorpWarSurrenderMsg
        s = ("[War] {against} has surrendered to {declaredBy}."
             .format(**fields))
        self.notify_channel("#grd", s)

    def notify_7(self, timestamp, fields):
        # 7: notificationTypeAllWarRetractedMsg
        s = ("[War] {declaredBy} has retracted the war against {against}."
             .format(**fields))
        self.notify_channel("#grd", s)

    def notify_30(self, timestamp, fields):
        # 30: notificationTypeCorpWarRetractedMsg
        s = ("[War] {declaredBy} has retracted the war against {against}."
             .format(**fields))
        self.notify_channel("#grd", s)

    def notify_8(self, timestamp, fields):
        # 8: notificationTypeAllWarInvalidatedMsg
        s = ("[War] CONCORD invalidates the war declared by {declaredBy} "
             "against {against} because {declaredBy} forgot to "
             "pay the bribe."
             .format(**fields))
        self.notify_channel("#grd", s)

    def notify_31(self, timestamp, fields):
        # 31: notificationTypeCorpWarInvalidatedMsg
        s = ("[War] CONCORD invalidates the war declared by {declaredBy} "
             "against {againstName} because {declaredBy} forgot to "
             "pay the bribe."
             .format(**fields))
        self.notify_channel("#grd", s)

    def notify_11(self, timestamp, fields):
        # 11: Bill not paid because there's not enough ISK available
        bill_typeid = fields['billTypeID']
        due_date = wintime_to_datetime(long(fields['dueDate']))
        s = ("[Bill] Gradient can't pay a bill (typeID {bill_typeid}), "
             "due at {due}, because the relevant wallet balance is too low."
             .format(bill_typeid=bill_typeid,
                     due=due_date.strftime("%Y-%m-%d %H:%M:%S")))
        self.notify_channel("#grd", s)


def wintime_to_datetime(timestamp):
    return datetime.datetime.utcfromtimestamp(
        (timestamp - 116444736000000000L) / 10000000
        )
