import datetime
import logging
import threading
import time
import urllib
import Queue
from xml.etree import ElementTree

from django.db import connection, transaction

from emtools.ccpeve.models import APIKey, apiroot

import killinfo
from models import Feed, Kill, Pilot, Corporation, Alliance, Faction

log = logging.getLogger('feedfetcher')

FETCH_THREAD_COUNT = 3
WRITE_THREAD_COUNT = 1
MAX_ATTEMPTS = 5
KILLQ_SIZE = 200

FETCHERCLASS = {}

def fetch_all_feeds():
    stats = Stats()
    feeds = {}
    feedq = Queue.Queue()
    evscofeedq = Queue.Queue()
    killq = Queue.Queue(maxsize=KILLQ_SIZE)

    start = datetime.datetime.now()

    for feed in Feed.objects.exclude(disabled=True):
        stats.add_feed()
        feeds[feed.id] = feed
        f = file("/tmp/foo.txt", "a")
        f.write("%r +\n" % ((feed.id, feed.feedtype, feed.url, feed.state),))
        f.close()
        feedq.put((feed.id, feed.feedtype, feed.url, feed.state))
    for url in get_evsco_feeds():
        #stats.add_feed()
        #evscofeedq.put((None, 'evsco', url, None))
        pass

    for ign in range(FETCH_THREAD_COUNT):
        t = FetcherThread(feedq, killq, stats)
        t.start()

    for ign in range(FETCH_THREAD_COUNT):
        t = EVSCOFetcherThread(evscofeedq, killq, stats)
        t.start()

    for ign in range(WRITE_THREAD_COUNT):
        t = WriterThread(feeds, killq, stats)
        t.start()

    waiter = threading.Thread(target=join_queues,
                              args=([feedq, evscofeedq, killq],))
    waiter.daemon = True
    waiter.start()

    log.info("Started fetching of %s feeds" % stats.numfeeds)

    waiter.join(60*60)
    while waiter.is_alive():
        log.info("feedq %s (%s), feedq2 %s (%s), killq %s (%s), numfeeds %s, "
                 "numerrorfeeds %s, totalkills %s, totalcreated %s" %
                 (feedq.qsize(), feedq.unfinished_tasks,
                  evscofeedq.qsize(), evscofeedq.unfinished_tasks,
                  killq.qsize(), killq.unfinished_tasks,
                  stats.numfeeds, stats.numerrorfeeds,
                  stats.totalkills, stats.totalcreated))
        waiter.join(60*60)

    end = datetime.datetime.now()
    log.info("Fetched %s new kills (based on %s kill infos) from %s feeds "
             "(%i of which failed) in %s"
             % (stats.totalcreated, stats.totalkills, stats.numfeeds,
                stats.numerrorfeeds, end - start))

def join_queues(queue_list):
    for q in queue_list:
        q.join()

class Stats(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.totalkills = 0
        self.totalcreated = 0
        self.numfeeds = 0
        self.numerrorfeeds = 0

    def add_kill(self, created=True):
        with self.lock:
            self.totalkills += 1
            if created:
                self.totalcreated += 1

    def add_error_feed(self):
        with self.lock:
            self.numerrorfeeds += 1

    def add_feed(self):
        with self.lock:
            self.numfeeds += 1

class WriterThread(threading.Thread):
    def __init__(self, feeds, killq, stats):
        super(WriterThread, self).__init__()
        self.daemon = True
        self.feeds = feeds
        self.killq = killq
        self.stats = stats
        self.entity_cache = EntityCache()

    def run(self):
        while True:
            (cmd, args) = self.killq.get()
            if cmd == 'kill':
                (kill,) = args
                self.handle_kill(kill)
            elif cmd == 'feeddone':
                (feedid, state, error) = args
                self.handle_feed_done(feedid, state, error)
            else:
                # wut?!
                raise RuntimeError('Unknown command %s' % cmd)
            self.killq.task_done()

    def handle_kill(self, kill):
        obj, created = Kill.objects.get_or_create_from_killinfo(
            kill, self.entity_cache)
        transaction.commit_unless_managed()
        self.stats.add_kill(created)

    def handle_feed_done(self, feedid, state, error):
        if feedid is None: # EVSCO
            transaction.commit_unless_managed()
            return
        feed = self.feeds[feedid]
        del self.feeds[feedid]
        feed.state = state
        feed.save()
        if error is None:
            feed.error = ''
            feed.failed_attempts = 0
        else:
            feed.error = error[0:250]
            feed.failed_attempts += 1
            if feed.failed_attempts > MAX_ATTEMPTS:
                log.info("Disabling feed %s (%s) after %s errors: %s" %
                         (feed.id, feed.url, MAX_ATTEMPTS, feed.error))
                feed.disabled = True
            feed.save()
            self.stats.add_error_feed()
        transaction.commit_unless_managed()

class FetcherThread(threading.Thread):
    def __init__(self, feedq, killq, stats):
        super(FetcherThread, self).__init__()
        self.daemon = True
        self.feedq = feedq
        self.killq = killq
        self.stats = stats

    def run(self):
        try:
            self.run2()
        except:
            logging.exception("Exception during FetcherThread run")

    def run2(self):
        while True:
            (feedid, feedtype, url, state) = self.feedq.get()
            try:
                fetcher = FETCHERCLASS[feedtype](url)
                for kill in fetcher.fetch(state):
                    self.killq.put(('kill', (kill,)))
                state = fetcher.state
            except Exception as e:
                error = "%s: %s" % (e.__class__.__name__,
                                    str(e))
                self.stats.add_error_feed()
                self.killq.put(('feeddone', (feedid, state, error)))
            else:
                self.killq.put(('feeddone', (feedid, state, None)))
            f = file("/tmp/foo.txt", "a")
            f.write("%r -\n" % ((feedid, feedtype, url, state),))
            f.close()

            self.feedq.task_done()

class EVSCOFetcherThread(threading.Thread):
    def __init__(self, feedq, killq, stats):
        super(EVSCOFetcherThread, self).__init__()
        self.daemon = True
        self.feedq = feedq
        self.killq = killq
        self.stats = stats

    def run(self):
        while True:
            (feedid, feedtype, url, state) = self.feedq.get()
            for try_ in range(2):
                try:
                    fetcher = FETCHERCLASS[feedtype](url)
                    for kill in fetcher.fetch(state):
                        self.killq.put(('kill', (kill,)))
                    state = fetcher.state
                except NoDataError:
                    # EVSCO hiccup
                    time.sleep(60) # Wait a minute to see if it improves
                    continue
                except Exception as e:
                    error = "%s: %s" % (e.__class__.__name__,
                                        str(e))
                    self.stats.add_error_feed()
                    self.killq.put(('feeddone', (feedid, state, error)))
                    break # tries
                else:
                    self.killq.put(('feeddone', (feedid, state, None)))
                    break # tries
            self.feedq.task_done()


class BaseFeed(object):
    def __init__(self, url):
        self.url = url
        self.state = None

    def parse_page(self, **kwargs):
        if "?" in self.url:
            url = self.url + "&" + urllib.urlencode(kwargs)
        else:
            url = self.url + "?" + urllib.urlencode(kwargs)
        data = None
        try:
            data = urllib.urlopen(url).read()
            return self.parse(self.sanitize(data))
        except Exception as e:
            if data is None:
                log.error("Can't parse document at %s - %s: %s" %
                          (url, e.__class__.__name__, str(e)))
            else:
                log.error("Can't parse document at %s - %s: %s, data was %r" %
                          (url, e.__class__.__name__, str(e), data[0:100]))
            raise

    def sanitize(self, data):
        try:
            start = data.index("<eveapi")
            end = data.index("</eveapi>") + len("</eveapi>")
        except ValueError:
            raise NoDataError()
        return data[start:end]

    def parse(self, data):
        raise RuntimeError("parse() implemented in subclasses")

    def fetch(self, state):
        if state is None:
            state = self.get_initial_state()
        if state is None:
            # No initial state, i.e. no kills in the last 28d -
            # nothing to see here.
            return
        state = int(state)
        self.state = state
        laststate = state
        while True:
            for kill in self.fetch_single(state):
                state = max(state, kill.kill_internal_id)
                yield kill
            if state == laststate:
                self.state = laststate
                return
            laststate = state

class EDKFeed(BaseFeed):
    def parse(self, data):
        tree = ElementTree.fromstring(data)
        for item in tree.findall("channel/item"):
            ki = item.find("description").text
            ki.kill_internal_id = int(item.find("title").text)
            yield killinfo.parse_textinfo(ki.killinfo.strip() + "\n")

    def get_initial_state(self):
        ts = datetime.datetime.utcnow() - datetime.timedelta(days=56)
        year = ts.year
        week = ts.strftime("%W")
        year + week
        # FIXME!

    def fetch_single(self, state):
        return self.parse_page(master=1, friend=1, combined=1,
                               lastkllid=state)

class IDFeed(BaseFeed):
    def parse(self, data):
        return killinfo.parse_api_page(data)

    def get_initial_state(self):
        ts = datetime.datetime.utcnow() - datetime.timedelta(days=56)
        startdate = int(time.mktime(ts.timetuple()))
        state = None
        try:
            for kill in self.parse_page(allkills=1, startdate=startdate):
                if state is None:
                    state = kill.kill_internal_id
                else:
                    state = min(state, kill.kill_internal_id)
            return state
        except NoDataError:
            pass
        ts = datetime.datetime.utcnow() - datetime.timedelta(days=7)
        startdate = int(time.mktime(ts.timetuple()))
        try:
            for kill in self.parse_page(allkills=1, startdate=startdate):
                if state is None:
                    state = kill.kill_internal_id
                else:
                    state = min(state, kill.kill_internal_id)
            return state
        except NoDataError:
            pass
        try:
            for kill in self.parse_page(allkills=1):
                if state is None:
                    state = kill.kill_internal_id
                else:
                    state = min(state, kill.kill_internal_id)
            return state
        except NoDataError:
            raise
        return state

    def fetch_single(self, state):
        return self.parse_page(allkills=1, lastintID=state)
FETCHERCLASS['idfeed'] = IDFeed

# EVSCO feed fetcher
class EVSCOFeed(IDFeed):
    def get_initial_state(self):
        ts = datetime.datetime.utcnow() - datetime.timedelta(days=7)
        startdate = int(time.mktime(ts.timetuple()))
        state = None
        for kill in self.parse_page(allkills=1, startdate=startdate):
            if state is None:
                state = kill.kill_internal_id
            else:
                state = min(state, kill.kill_internal_id)
        return state
FETCHERCLASS['evsco'] = EVSCOFeed

def get_evsco_feeds(entities_per_feed=1):
    """
    Generate EVSCO feeds from our standings and all entities active in
    the Republic in the last 28 days.
    """
    key = APIKey.objects.get(name='Gradient')
    cl = key.corp().ContactList()
    api = apiroot()
    al = api.eve.AllianceList()
    all_alliances = set(a.allianceID for a in al.alliances)
    corpids = set()
    allianceids = set()
    for contact in cl.allianceContactList:
        if contact.contactID in all_alliances:
            allianceids.add(contact.contactID)
        else:
            corpids.add(contact.contactID)
    feeds = []
    for corpid in corpids:
        feeds.append("http://eve-kill.net/?a=idfeed&corp=%s" % corpid)
    for allianceid in allianceids:
        feeds.append("http://eve-kill.net/?a=idfeed&alliance=%s" % allianceid)
    return feeds
    # corpids = list(corpids)
    # corpidlists = [corpids[i:i+entities_per_feed]
    #                for i in range(0, len(corpids), entities_per_feed)]
    # for corpid_list in corpidlists:
    #     feeds.append("http://eve-kill.net/?a=idfeed&corp=%s" %
    #                  ",".join(str(x) for x in corpid_list))
    # allianceids = list(allianceids)
    # allianceidlists = [allianceids[i:i+entities_per_feed]
    #                    for i in range(0, len(allianceids), entities_per_feed)]
    # for allianceid_list in allianceidlists:
    #     feeds.append("http://eve-kill.net/?a=idfeed&alliance=%s" %
    #                  ",".join(str(x) for x in corpid_list))
    # return feeds

def clean_kills():
    old = datetime.datetime.now() - datetime.timedelta(days=28*2)
    c = connection.cursor()
    c.execute("DELETE FROM intel_kill_involvedpilots inv "
              "WHERE (SELECT timestamp FROM intel_kill "
              "       WHERE intel_kill.id = inv.kill_id "
              "      ) < %s",
              (old,))
    c.execute("DELETE FROM intel_kill_involvedcorps inv "
              "WHERE (SELECT timestamp FROM intel_kill "
              "       WHERE intel_kill.id = inv.kill_id "
              "      ) < %s",
              (old,))
    c.execute("DELETE FROM intel_kill_involvedalliances inv "
              "WHERE (SELECT timestamp FROM intel_kill "
              "       WHERE intel_kill.id = inv.kill_id "
              "      ) < %s",
              (old,))
    c.execute("DELETE FROM intel_kill_involvedfactions inv "
              "WHERE (SELECT timestamp FROM intel_kill "
              "       WHERE intel_kill.id = inv.kill_id "
              "      ) < %s",
              (old,))
    c.execute("DELETE FROM intel_kill WHERE timestamp < %s",
              (old,))

class EntityCache(object):
    def __init__(self):
        self.idcache = {}
        self.namecache = {}

    def get_generic(self, Model, idfield, itemid, name):
        self.idcache.setdefault(Model.__name__, {})
        idcache = self.idcache[Model.__name__]
        self.namecache.setdefault(Model.__name__, {})
        namecache = self.namecache[Model.__name__]
        if itemid == 0:
            itemid = None
        if name == "":
            name = None
        if itemid is not None and itemid in idcache:
            return idcache[itemid], False
        if name is not None and name.lower() in namecache:
            return namecache[name.lower()], False
        if itemid is not None:
            try:
                obj = Model.objects.get(**{idfield: itemid})
                idcache[getattr(obj, idfield)] = obj
                namecache[obj.name.lower()] = obj
                return obj, False
            except Model.DoesNotExist:
                pass
        if name is not None:
            try:
                obj = Model.objects.filter(
                    name__iexact=name
                    ).order_by('-lastseen')[0:1].get()
                idcache[getattr(obj, idfield)] = obj
                namecache[obj.name.lower()] = obj
                return obj, False
            except Model.DoesNotExist:
                pass
        return Model.objects.create(
            **{'name': "" if name is None else name,
               idfield: itemid}), True

    def get_pilot(self, itemid, name):
        return self.get_generic(Pilot, 'characterid', itemid, name)

    def get_corp(self, itemid, name):
        return self.get_generic(Corporation, 'corporationid', itemid, name)

    def get_alliance(self, itemid, name):
        return self.get_generic(Alliance, 'allianceid', itemid, name)

    def get_faction(self, itemid, name):
        return self.get_generic(Faction, 'factionid', itemid, name)

class NoDataError(Exception):
    pass
