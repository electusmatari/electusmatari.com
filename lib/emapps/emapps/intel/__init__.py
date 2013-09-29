import datetime
import re
import time

import cgi
import kgi

from emapps.util import eve_time
from emapps.util import require_permission

def intelapp(environ, start_response):
    URLCONF = [
        ('/stats/', view_stats),
        ('/submit/', view_submit),
        ('/', view_listing)
        ]
    return kgi.dispatch(environ, start_response, URLCONF)

@require_permission('em')
def view_listing(environ):
    form = cgi.FieldStorage()
    needle = form.getfirst("search", "")
    extra = ""
    extra_args = []
    if needle != "":
        extra += ("WHERE target LIKE %s "
                  "   OR system LIKE %s "
                  "   OR station LIKE %s "
                  "   OR agent LIKE %s "
                  "   OR submitter LIKE %s ")
        extra_args.extend(["%%%s%%" % needle] * 5)
    extra += "ORDER BY ts DESC, id DESC"
    page = kgi.paginate('locator_trace', dbname='dbforcer',
                        extra=extra, extra_args=extra_args)
    return kgi.template_response('intel/listing.html',
                                 user=environ['emapps.user'],
                                 current_time=eve_time(),
                                 traces=page,
                                 search=needle)

@require_permission('em')
def view_submit(environ):
    user = environ['emapps.user']
    if environ["REQUEST_METHOD"] == 'POST':
        form = cgi.FieldStorage()
        mail = form.getfirst("mail", "")
        success = add_trace(user, mail)
        if success:
            return kgi.redirect_response('http://www.electusmatari.com/intel/')
        else:
            return kgi.template_response('intel/submit.html',
                                         user=user,
                                         pagetype='malformed',
                                         error=mail)
    return kgi.template_response('intel/submit.html',
                                 user=environ['emapps.user'],
                                 pagetype="normal")

MAIL_RX = [re.compile("I found (?P<target>.*?) for you\n"
                      "From: *(?P<agent>.*?)\n"
                      "Sent: *(?P<ts>[0-9][0-9][0-9][0-9]\\.[0-9][0-9]\\.[0-9][0-9] [0-9][0-9]:[0-9][0-9]).*\n"
                      "\n"
                      "The sleazebag is currently at (?P<station>.*?) station in the (?P<system>.*?) system"),
           re.compile("I found (?P<target>.*?) for you\n"
                      "From: *(?P<agent>.*?)\n"
                      "Sent: *(?P<ts>[0-9][0-9][0-9][0-9]\\.[0-9][0-9]\\.[0-9][0-9] [0-9][0-9]:[0-9][0-9]).*\n"
                      "\n"
                      "The sleazebag is currently in the (?P<system>.*?) system"),
           re.compile("I found (?P<target>.*?) for you\n"
                      "From: *(?P<agent>.*?)\n"
                      "Sent: *(?P<ts>[0-9][0-9][0-9][0-9]\\.[0-9][0-9]\\.[0-9][0-9] [0-9][0-9]:[0-9][0-9]).*\n"
                      "\n"
                      "The scumsucker is located in the (?P<system>.*?) system,"),
           re.compile("I found (?P<target>.*?) for you\n"
                      "From: *(?P<agent>.*?)\n"
                      "Sent: *(?P<ts>[0-9][0-9][0-9][0-9]\\.[0-9][0-9]\\.[0-9][0-9] [0-9][0-9]:[0-9][0-9]).*\n"
                      "\n"
                      "The scumsucker is located at (?P<station>.*?) station in the (?P<system>.*?) system,"),
           ]

def add_trace(user, mail):
    for rx in MAIL_RX:
        m = rx.search(mail.replace("\r", ""))
        if m is None:
            continue
        d = m.groupdict()
        (target, agent, ts, system) = (d['target'],
                                       d['agent'],
                                       d['ts'],
                                       d['system'])
        ts = time.strptime(ts, "%Y.%m.%d %H:%M")
        ts = datetime.datetime(*ts[:6])
        station = d.get('station', None)
        db = kgi.connect('dbforcer')
        c = db.cursor()
        c.execute("INSERT INTO locator_trace (ts, target, system, station, "
                  "                           agent, submitter) "
                  "VALUES (%s, %s, %s, %s, %s, %s)",
                  (ts.strftime("%Y-%m-%d %H:%M"),
                   target, system, station, agent, user.username))
        return True
    return False

@require_permission('em')
def view_stats(environ):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("SELECT COUNT(*) AS c, submitter "
              "FROM locator_trace "
              "GROUP BY submitter "
              "ORDER BY c DESC")
    return kgi.template_response('intel/stats.html',
                                 user=environ['emapps.user'],
                                 stats=c.fetchall())
