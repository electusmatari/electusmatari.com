import cgi
import datetime
import re

import kgi
import tempita

from emapps.util import eve_time
from emapps.util import require_permission

PREFIX_TOSET = ["Set standing"]
PREFIX_DIPLO = ["Needs diplomat's attention"]
PREFIX_ACT = ["In action"]

standings_forums = { 'em': 19, 'grd': 169 }

def standingsapp(environ, start_response):
    URLCONF = [
        ('^/check/', standings_check),
        ('^/rc/', view_rc),
        ('^/crimes/', view_crimes),
        ('^/$', view_standings)
    ]
    return kgi.dispatch(environ, start_response, URLCONF)

def standings_check(environ):
    user = environ['emapps.user']
    if not user.has_permission(environ["org"]):
        return kgi.html_response(
            unauthorized(user, 'You are not authorized.')
            )
    tids = {}
    bogus = []
    to_set = []
    to_diplo = []
    to_act = {}
    now = datetime.datetime.utcnow()
    for (tid, subject, edittime, prefix, editor) in get_threads(standings_forums[environ["org"]]):
        try:
            edittime = datetime.datetime.utcfromtimestamp(edittime)
        except:
            edittime = now
        p = parse_subject(subject)
        if p is None:
            bogus.append((subject, tid))
        else:
            (entity, ticker, standing, comments, internal) = p
            tids.setdefault(entity, [])
            tids[entity].append((subject, tid))
            if prefix in PREFIX_TOSET:
                age = (now - edittime).days
                to_set.append((subject, tid, age))
            elif prefix in PREFIX_DIPLO:
                age = (now - edittime).days
                to_diplo.append((subject, tid, age))
            elif prefix in PREFIX_ACT:
                age = (now - edittime).days
                if editor is None:
                    editor = "None?"
                to_act.setdefault(editor, [])
                to_act[editor].append((subject, tid, age))
    dups = []
    for (entity, threads) in tids.items():
        if len(threads) > 1:
            dups.append((entity, threads))
    bogus.sort()
    dups.sort()
    to_act = to_act.items()
    to_act.sort(lambda a, b: cmp((a[0].lower(), a[1]), (b[0].lower(), b[1])))
    return kgi.template_response('standings/check.html',
                                 user=environ["emapps.user"],
                                 current_time=eve_time(),
                                 to_diplo=to_diplo,
                                 to_set=to_set,
                                 to_act=to_act,
                                 bogus=bogus,
                                 dups=dups)

def view_crimes(environ):
    return kgi.template_response('standings/crimes.html',
                                 user=environ["emapps.user"])

def view_standings(environ):
    update_rc(environ)
    positive = []
    negative = []
    for (tid, subject, edittime, prefix, editor) in get_threads(standings_forums[environ["org"]]):
        p = parse_subject(subject)
        if p is None:
            continue
        (entity, ticker, standing, comments, internal) = p
        standing = normalize_standing(standing)
        if standing == 0:
            continue
        b = tempita.bunch(entity=entity,
                          ticker=ticker,
                          standing=standing,
                          comments=comments,
                          tid=tid)
        if standing > 0:
            positive.append(b)
        else:
            negative.append(b)
    positive.sort(lambda a, b: cmp(a.entity.lower(), b.entity.lower()))
    negative.sort(lambda a, b: cmp(a.entity.lower(), b.entity.lower()))
    form = cgi.FieldStorage()
    format = form.getfirst("format", "html")
    if (format == 'igb'
        or (format == 'html'
            and environ["HTTP_USER_AGENT"].startswith("EVE-minibrowser"))):
        return kgi.template_response('standings/list_igb.html',
                              positive=positive,
                              negative=negative)
    elif format == 'xml':
        return kgi.template_response('standings/list_xml.html',
                                     header=[('Content-Type', 'text/xml')],
                                     standings=positive + negative)
    else:
        return kgi.template_response('standings/list.html',
                                     user=environ['emapps.user'],
                                     current_time=eve_time(),
                                     positive=positive,
                                     negative=negative)

def view_rc(environ):
    update_rc(environ)
    page = kgi.paginate('standings_rc',
                        dbname='dbforcer',
                        extra='ORDER BY date DESC, entity ASC')
    return kgi.template_response('standings/rc.html',
                                 user=environ['emapps.user'],
                                 current_time=eve_time(),
                                 page=page)

def update_rc(environ):
    last = dict((entity.lower(), standing) for (entity, standing)
                in get_last_standings())
    current = {}
    changes = []
    for (tid, subject, edittime, prefix, editor) in get_threads(standings_forums[environ["org"]]):
        p = parse_subject(subject)
        if p is None:
            continue
        (entity, ticker, standing, comments, internal) = p
        standing = normalize_standing(standing)
        name = entity.lower()
        if name not in current:
            current[name] = []
        current[name].append((entity, ticker, standing, tid))
    for (name, entries) in current.items():
        # Ignore duplicates
        if len(entries) > 1:
            del current[name]
            if name in last:
                del last[name]
        old_standing = last.get(name, 0)
        (entity, ticker, new_standing, tid) = entries[0]
        if old_standing != new_standing:
            add_standings_change(entity, ticker,
                                 old_standing, new_standing,
                                 tid)
            if name in current:
                del current[name]
            if name in last:
                del last[name]
    for (name, old_standing) in last.items():
        if name in current:
            (entity, ticker, new_standing, tid) = current[name][0]
        else:
            (entity, ticker, new_standing, tid) = (name, '', 0, 0)
        if old_standing != new_standing:
            add_standings_change(entity, ticker,
                                 old_standing, new_standing,
                                 tid)
            # If we do this, we can check at the end that both lists
            # are empty. Ignore for now.

            # if name in current:
            #     del current[name]
            # if name in last:
            #     del last[name]

subj_rx = re.compile("([-A-Za-z0-9_.' ]*?) "
                     "([<[].*?[]>])"
                     " +- +"
                     "(-10|-5|[Nn]eutral|\\+5|\\+10)"
                     "(?:, )?([^(]*)"
                     "(?: \\((.*)\\))?$")
def parse_subject(subject):
    m = subj_rx.match(subject)
    if not m:
        return None
    (entity, ticker, standing, comments, internal) = m.groups()
    return (entity, ticker, standing, comments, internal)

SQL_THREADS = """
SELECT t.tid, t.subject, GREATEST(p.dateline, p.edittime), prefix.prefix, eu.username
FROM mybb_forums AS f
     INNER JOIN mybb_threads AS t
       ON f.fid = t.fid
     LEFT JOIN mybb_threadprefixes AS prefix
       ON t.prefix = prefix.pid
     LEFT JOIN mybb_posts AS p
       ON t.firstpost = p.pid
     LEFT JOIN mybb_users AS eu
       ON (CASE p.edituid WHEN 0 THEN p.uid ELSE p.edituid END) = eu.uid
WHERE f.fid = {forumid}
  AND t.sticky = 0
ORDER BY t.subject
;
"""
def get_threads(standingsforum):
    db = kgi.connect('dbforums')
    c = db.cursor()
    c.execute(SQL_THREADS.format(forumid=standingsforum))
    return c.fetchall()

SQL_LAST_STANDINGS = """
SELECT entity, new_standing
FROM standings_rc AS s1
WHERE date = (SELECT MAX(date)
              FROM standings_rc AS s2
              WHERE s2.entity = s1.entity);
"""
def get_last_standings():
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute(SQL_LAST_STANDINGS)
    return c.fetchall()

SQL_INSERT_RC = """
INSERT INTO standings_rc (entity, ticker, old_standing, new_standing, tid)
VALUES (%s, %s, %s, %s, %s)
"""
def add_standings_change(entity, ticker, old_standing, new_standing, tid):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute(SQL_INSERT_RC,
              (entity, ticker, old_standing, new_standing, tid))

def normalize_standing(st):
    try:
        st = int(st)
    except:
        st = 0
    if st > 0:
        st = 5
    if st < 0:
        st = -10
    return st
