import cgi
import datetime
import logging

import kgi
import eveapi

from emapps.util import eve_time, require_permission

log = logging.getLogger('ops')

def opsapp(environ, start_response):
    URLCONF = [
        ('^/window/', view_window),
        ('^/oplist/', view_oplist),
        ('^/', view_info),
        ]
    return kgi.dispatch(environ, start_response, URLCONF)

@require_permission('em')
def view_info(environ):
    user = environ['emapps.user']
    if environ['REQUEST_METHOD'] == 'POST':
        # FIXME! Check FC permission here.
        form = cgi.FieldStorage()
        optitle = form.getfirst("title")
        db = kgi.connect('dbforcer')
        c = db.cursor()
        c.execute("INSERT INTO opwarn_list (title) VALUES (%s)",
                  (optitle,))
        return kgi.redirect_response('http://www.electusmatari.com/ops/')
    return kgi.template_response('ops/info.html',
                                 user=user)

@require_permission('em')
def view_window(environ):
    return kgi.template_response('ops/window.html',
                                 user=environ['emapps.user'])

@require_permission('em')
def view_oplist(environ):
    import simplejson as json
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("SELECT id, created, title FROM opwarn_list "
              "WHERE created > NOW() - INTERVAL 1 HOUR "
              "ORDER BY created DESC LIMIT 1")
    if c.rowcount == 0:
        return kgi.html_response(json.dumps({}),
                                 header=[('Content-Type', 'application/json')]
                                 )
    (id, created, title) = c.fetchone()
    delta = datetime.datetime.utcnow() - created
    return kgi.html_response(json.dumps({'id': id,
                                         'created': eve_time(created),
                                         'seconds': delta.seconds,
                                         'title': title}),
        header=[('Content-Type', 'application/json')]
        )

# CREATE TABLE opwarn_list (
#   id SERIAL,
#   created TIMESTAMP DEFAULT NOW(),
#   title VARCHAR(255)
# )
