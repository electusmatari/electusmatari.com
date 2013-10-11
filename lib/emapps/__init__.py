import logging
import wsgiref
import wsgiref.util

import kgi
import mybb_auth

from emapps.responses import notfound

def emapps(environ, start_response):
    log = logging.getLogger()
    log.setLevel(logging.DEBUG)
    dbh = DBLogHandler()
    dbh.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s %(name)-10s %(levelname)-10s "
                                  "%(message)s",
                                  "%Y-%m-%d %H:%M:%S")
    dbh.setFormatter(formatter)
    log.addHandler(dbh)

    environ['emapps.user'] = User(*mybb_auth.mybb_auth(environ))
    app = wsgiref.util.shift_path_info(environ)
    if app == 'standings':
        import standings
        data = standings.standingsapp(environ, start_response)
    elif app == 'gradient':
        import gradient
        data = gradient.grdapp(environ, start_response)
    elif app == 'forumtools':
        import forums
        data = forums.forumsapp(environ, start_response)
    else:
        start_response('404 Not Found', [('Content-Type', 'text/html')])
        data = notfound().encode("utf-8")
    return data

class DBLogHandler(logging.Handler):
    def emit(self, record):
        db = kgi.connect('dbforcer')
        c = db.cursor()
        c.execute("INSERT INTO log (log) VALUES (%s)",
                  ( self.format(record), ))

class User(object):
    def __init__(self, username, is_emuser):
        self.username = username
        self.is_emuser = is_emuser
        self.permissions = None

    def is_authenticated(self):
        return self.username != 'Anonymous'

    def has_permission(self, name):
        if name == 'em':
            return self.is_emuser
        if self.permissions is None:
            db = kgi.connect('dbforcer')
            c = db.cursor()
            c.execute("""
SELECT permission FROM userpermissions
WHERE username = %s
""", (self.username,))
            self.permissions = [x for (x,) in c.fetchall()]
        return name in self.permissions

# CREATE TABLE userpermissions (
#   id SERIAL PRIMARY KEY,
#   username VARCHAR(255),
#   permission VARCHAR(255)
# );
