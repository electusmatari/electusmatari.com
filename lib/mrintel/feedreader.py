import logging
import threading
import time

import feedparser

SECONDS_BETWEEN_PULLS = 5 * 60


class Feedreader(threading.Thread):
    def __init__(self, conf, bot):
        super(Feedreader, self).__init__()
        self.daemon = True
        self.bot = bot
        self.feeds = []
        for sec in conf.sections():
            if not sec.startswith("feed "):
                continue
            channels = [chan.strip()
                        for chan in conf.get(sec, 'channels').split(",")]
            self.feeds.append({'name': conf.get(sec, 'name'),
                               'url': conf.get(sec, 'url'),
                               'channels': channels,
                               'initialized': False,
                               'seen': set()})
        self.conf = conf

    def run(self):
        while True:
            try:
                self.run2()
            except:
                logging.exception("Exception during Feedreader.run()")
                time.sleep(5 * 60)

    def run2(self):
        while True:
            for feed in self.feeds:
                self.handle_feed(feed)
            time.sleep(SECONDS_BETWEEN_PULLS)

    def handle_feed(self, feed):
        data = feedparser.parse(feed['url'])
        if len(data.entries) == 0:
            return
        new_seen = set()
        for entry in data.entries:
            if feed['initialized'] and entry.link not in feed['seen']:
                self.announce(feed, entry)
            new_seen.add(entry.link)
        feed['seen'] = new_seen
        feed['initialized'] = True

    def announce(self, feed, entry):
        for channel in feed['channels']:
            self.bot.msg(channel, "[{name}] {entry.title} - {entry.link}"
                         .format(name=feed['name'], entry=entry))
