import logging
import threading

from mrintel.eve.api import EVEAPI
from mrintel.eve import pricecheck
from mrintel.eve import iteminfo
from mrintel.eve import hot
from mrintel.eve import patrol


def dont_parse_args(fun):
    fun.dont_parse_args = True
    return fun


class EVEBotMixIn(object):
    def defer_to_thread(self, target, sender, channel, *args):
        def handler():
            try:
                target(sender, channel, *args)
            except:
                self.reply(sender, channel, "I am terribly sorry, but "
                           "there was an error processing your command. "
                           "Admins have been notified.")
                logging.exception("Exception during {0}:".format(
                        target.__name__))
        t = threading.Thread(target=handler)
        t.daemon = True
        t.start()

    def cmd_TQ(self, sender, channel):
        """
        Return the current Tranquility server status as reported by the EVE API.
        """
        self.defer_to_thread(self.thread_TQ, sender, channel)

    def thread_TQ(self, sender, channel):
        with EVEAPI(sender, channel) as apiroot:
            status = apiroot.server.ServerStatus()
            self.reply(sender, channel,
                       "Server {0}, {1} players online"
                       .format("open" if status.serverOpen == 'True'
                               else "closed",
                               status.onlinePlayers))

    @dont_parse_args
    def cmd_PC(self, sender, channel, typename):
        """
        Return a market quote for the given type name.
        """
        self.defer_to_thread(self.thread_PC, sender, channel, typename)

    def thread_PC(self, sender, channel, typename):
        price = pricecheck.pricecheck(typename)
        self.reply(sender, channel, pricecheck.format_reply(price, typename))

    @dont_parse_args
    def cmd_INFO(self, sender, channel, itemname):
        """
        Return info about an object in the game world.
        """
        self.defer_to_thread(self.thread_INFO, sender, channel, itemname)

    def thread_INFO(self, sender, channel, itemname):
        infostring = iteminfo.iteminfo(itemname)
        self.reply(sender, channel, iteminfo.format_reply(infostring))

    def cmd_HOT(self, sender, channel):
        """
        Show the low-sec systems in the Republic and the war zone with the most kills.
        """
        self.defer_to_thread(self.thread_HOT, sender, channel)

    def thread_HOT(self, sender, channel):
        self.reply(sender, channel, hot.hot())

    def cmd_PATROL(self, sender, channel, startsystem="Pator", maxlength=23):
        """
        Suggest a patrol route through hot systems. Usage: !patrol [startsystem] [maxlength]
        """
        self.defer_to_thread(self.thread_PATROL, sender, channel,
                             startsystem, int(maxlength))

    def thread_PATROL(self, sender, channel, startsystem, maxlength):
        self.reply(sender, channel, patrol.patrol(startsystem, maxlength))

    def cmd_PATROLFW(self, sender, channel, startsystem="Pator", maxlength=23):
        """
        Suggest a patrol route through contested systems. Usage: !patrolfw [startsystem] [maxlength]
        """
        self.defer_to_thread(self.thread_PATROLFW, sender, channel,
                             startsystem, int(maxlength))

    def thread_PATROLFW(self, sender, channel, startsystem, maxlength):
        self.reply(sender, channel,
                   patrol.patrolcontested(startsystem, maxlength))
