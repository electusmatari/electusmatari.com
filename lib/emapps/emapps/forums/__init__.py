import cgi
import datetime

import kgi

from emapps.util import require_permission
from emapps.util import eve_time

def forumsapp(environ, start_response):
    """
    Main application interface. Dispatch over pages.
    """
    URLCONF = [
        ('^/reputation/', view_reputation),
    ]
    return kgi.dispatch(environ, start_response, URLCONF)

@require_permission('em')
def view_reputation(environ):
    db = kgi.connect('dbforums')
    c = db.cursor()
    c.execute("SELECT u.uid, u.username, addu.uid, addu.username, "
              "       r.reputation, r.dateline, r.comments, r.pid "
              "FROM mybb_reputation r "
              "     INNER JOIN mybb_users u ON r.uid = u.uid "
              "     INNER JOIN mybb_users addu ON r.adduid = addu.uid "
              "ORDER BY r.dateline DESC "
              "LIMIT 23")
    reputation = [(uid, username, adduid, addusername, reputation,
                   datetime.datetime.utcfromtimestamp(dateline),
                   comments, pid)
                  for (uid, username, adduid, addusername, reputation,
                       dateline, comments, pid)
                  in c.fetchall()]
    return kgi.template_response('forums/reputation.html',
                                 user=environ["emapps.user"],
                                 reputation=reputation)

