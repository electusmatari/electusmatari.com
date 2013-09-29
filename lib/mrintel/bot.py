import irclib
import threading

import mrintel.eve.commands as evecommands
from mrintel import feedreader

from mrintel.eve import notifications
from mrintel.eve import apicheck

class MrIntel(irclib.IRCBot, evecommands.EVEBotMixIn):
    version = "MrIntel, your friendly neighborhood intelligence officer"

    def __init__(self, conf, server, port, nick, user, realname, channels):
        super(MrIntel, self).__init__(server, port, nick, user, realname,
                                      channels)
        self.conf = conf
        self.feedreader = feedreader.Feedreader(conf, self)
        self.feedreader.start()
        self.calendar = notifications.CalendarWatcher(self)
        self.calendar.start()
        self.notifications = notifications.NotificationWatcher(self)
        self.notifications.start()
        self.apicheck = apicheck.APICheck(self)
        self.apicheck.start()

    def on_ctcp_ACTION(self, sender, target, args):
        if args.startswith('pats {0}'.format(self.mynick)):
            if target is None:
                self.ctcp(sender.nick, "ACTION", "beams.")
            else:
                self.ctcp(target, "ACTION", "beams.")

    def on_ctcp_VERSION(self, sender, target, args=None):
        self.ctcp_reply(sender.nick, "VERSION", self.version)

    def cmd_STATUS(self, sender, channel):
        """
        Report some current stats about the bot.
        """
        import threading
        import os
        stat = os.statvfs("/")
        hdfree = stat.f_favail * stat.f_bsize
        hdtotal = stat.f_blocks * stat.f_bsize
        for line in open("/proc/meminfo"):
            if line.startswith("MemTotal:"):
                memtotal = int(line.split()[1])
            elif line.startswith("MemFree:"):
                memfree = int(line.split()[1])
        loadavg = ", ".join(open("/proc/loadavg").read().split()[0:3])
        self.reply(sender, channel,
                   "I'm running {nthreads} threads. "
                   "{hdfree:.1f} GB disk space free ({hdused:.1f}% used). "
                   "{memfree:.1f} GB memory free ({memused:.1f}% used). "
                   "Load average: {loadavg}"
                   .format(nthreads=threading.active_count(),
                           hdfree=hdfree/1024.0/1024/1024,
                           hdused=(1-(hdfree/float(hdtotal)))*100,
                           memfree=memfree/1024.0/1024,
                           memused=(1-(memfree/float(memtotal)))*100,
                           loadavg=loadavg
                           ))

    def cmd_JOIN(self, sender, channel, target):
        """
        Make MrIntel join a given channel.
        """
        self.join_channel(target)
        self.msg(target, "Hello! {0} asked me to join here. Just use "
                 "{1}part to get rid of me.".format(sender.nick,
                                                    self.command_char))

    def cmd_PART(self, sender, channel):
        """
        Ask MrIntel to leave the current channel.
        """
        if channel is None:
            self.reply(sender, channel,
                       "Use the PART command in a channel, not in a query")
        else:
            self.part_channel(channel)

    def cmd_CALC(self, sender, channel, expression):
        """
        Calculate an expression using Google's calculator.
        """
        t = threading.Thread(target=self.thread_CALC,
                             args=(sender, channel, expression))
        t.daemon = True
        t.start()
    cmd_CALC.dont_parse_args = True

    def thread_CALC(self, sender, channel, expression):
        try:
            import urllib, re
            url = urllib.urlopen("http://www.google.com/ig/calculator?" +
                                 urllib.urlencode({
                        'hl': 'en',
                        'q': expression}))
            data = url.read().decode("latin-1")
            # Not valid JSON :-(
            fields = dict(re.findall('[{,]([a-z]*): "(.*?)"', data))
            if fields['error'] == '':
                self.reply(sender, channel,
                           u"{0} is {1}".format(fields['lhs'],
                                                fields['rhs']))
            else:
                self.reply(sender, channel,
                           u"That looked malformed. Could you try to "
                           u"rephrase?")
        except:
            import logging
            self.reply(sender, channel, "I am terribly sorry, but "
                       "there was an error processing your command. "
                       "Admins have been notified.")
            logging.exception("Exception during cmd_CALC:")
