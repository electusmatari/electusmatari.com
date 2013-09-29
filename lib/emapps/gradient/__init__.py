# Gradient utility functions

import csv
import datetime
import kgi
import os
import pickle

import simplejson
import tempita

from emapps.responses import unauthorized
from emapps.util import require_permission
from emapps.util import eve_time

MEMBERFILE = "/home/forcer/Projects/old-emcom/ftp/data/grd-personnel.txt"
PRICESFILE = "/home/forcer/Projects/old-emcom/ftp/data/grd-pricelist.txt"
MORDERFILE = "/home/forcer/Projects/old-emcom/ftp/data/grd-marketorders.txt"
PLANETFILE = "/home/forcer/Projects/old-emcom/ftp/data/grd-pi.txt"

def grdapp(environ, start_response):
    URLCONF = [
        ('^/prices/', view_prices),
        ('^/members/', view_members),
        ('^/voters/', view_voters),
        ('^/production/', view_price_comparison),
        ('^/orders/', view_market),
        ('^/pi/', view_pi),
        ('^/', view_main),
        ]
    return kgi.dispatch(environ, start_response, URLCONF)

def require_gradient(require_admin=True):
    def sentinel(func):
        def handler(environ, *args, **kwargs):
            user = environ['emapps.user']
            if require_admin and not user.has_permission('corpadmin'):
                return kgi.html_response(
                    unauthorized(user, 'You are not an admin.')
                    )
            db = kgi.connect('dbdjango')
            c = db.cursor()
            c.execute("SELECT corp FROM emauth_profile "
                      "WHERE mybb_username = %s AND active",
                      (user.username,))
            if c.rowcount == 0:
                return kgi.html_response(
                    unauthorized(user, 'You are not API authenticated.')
                    )
            corpname = c.fetchone()[0]
            if corpname != 'Gradient':
                return kgi.html_response(
                    unauthorized(user, 'You are not in Gradient.')
                    )
            return func(environ, *args, **kwargs)
        return handler
    return sentinel

@require_gradient(False)
def view_main(environ):
    user = environ["emapps.user"]
    return kgi.template_response('gradient/index.html',
                                 user=user)

@require_gradient(False)
def view_prices(environ):
    user = environ["emapps.user"]
    data = simplejson.dumps([[row[0], float(row[1])]
                             for row
                             in csv.reader(file(PRICESFILE))])
    return kgi.template_response('gradient/pricelist.html',
                                 user=user,
                                 data=data)

@require_gradient(False)
def view_price_comparison(environ):
    user = environ["emapps.user"]
    data = simplejson.dumps([[tn, float(prod), float(heim), long(vol),
                              float(jita), last]
                             for (tn, prod, heim, vol, jita, last)
                             in list(csv.reader(file(PRICESFILE)))])
    return kgi.template_response('gradient/price_comparison.html',
                                 user=user,
                                 data=data)

@require_gradient(False)
def view_pi(environ):
    user = environ["emapps.user"]
    data = simplejson.dumps([[tn, float(index), float(prod), float(profit),
                              long(mov), float(jita_index), float(jita_prod)]
                             for (tn, index, prod, profit, mov, jita_index,
                                  jita_prod)
                             in list(csv.reader(file(PLANETFILE)))])
    return kgi.template_response('gradient/pi.html',
                                 user=user,
                                 data=data)

@require_gradient()
def view_members(environ):
    user = environ["emapps.user"]

    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("SELECT username FROM auth_user "
              "WHERE corp = 'Gradient' "
              " AND authenticated = 1 "
              "ORDER BY username ASC")
    forumusers = [x.lower() for (x,) in c.fetchall()]
    db2 = kgi.connect('dbforums')
    c2 = db2.cursor()
    c2.execute("SELECT username, usertitle FROM mybb_users "
               "WHERE CONCAT(',', usergroup, ',', additionalgroups, ',') "
               "      LIKE '%,56,%' "
               "ORDER BY username ASC")
    forumusers.extend([username.lower()
                       for (username, usertitle) in c2.fetchall()
                       if (usertitle == 'Gradient'
                           or usertitle.startswith('Gradient' + " / "))])
    datatime = datetime.datetime.fromtimestamp(os.stat(MEMBERFILE).st_mtime)
    members = pickle.load(file(MEMBERFILE))
    now = datetime.datetime.utcnow()
    inactive = []
    promotion = []
    prospects = []
    notonforums = []
    missingtitles = []
    directroles = []
    for name, details in members.items():
        charid = details['characterID']
        freeformtitle = details['freeformtitle']
        titles = details['titles']
        roles = details['roles']
        start = details['startDateTime']
        logon = details['logonDateTime']
        logoff = details['logoffDateTime']
        if "on leave" in freeformtitle.lower():
            continue
        if name.lower() not in forumusers:
            if (now - logoff).days > 30:
                note = "inactive"
            elif 'Prospect' in titles:
                note = "prospect"
            else:
                note = ""
            notonforums.append((name, charid, note))
        if (now - logoff).days > 30:
            inactive.append((name, charid, logoff, roles == 0L))
        elif 'Prospect' in titles:
            prospects.append((name, charid, start, logoff))
            if (now - start).days > 30:
                promotion.append((name, charid, start))
        if 'Director' not in titles and 'Employee' not in titles and 'Prospect' not in titles:
            missingtitles.append((name, charid, titles))
        if len(roles) > 0:
            directroles.append((name, charid, roles))
    members = members.items()
    members.sort(lambda a, b: cmp(a[0], b[0]))
    inactive.sort(lambda a, b: cmp(a[2], b[2]))
    promotion.sort(lambda a, b: cmp(a[2], b[2]))
    prospects.sort(lambda a, b: cmp(a[0], b[0]))
    notonforums.sort(lambda a, b: cmp(a[0], b[0]))
    missingtitles.sort(lambda a, b: cmp(a[0], b[0]))
    directroles.sort(lambda a, b: cmp(a[0], b[0]))
    return kgi.template_response('gradient/members.html',
                                 user=user,
                                 now=now,
                                 datatime=datatime,
                                 members=members,
                                 inactive=inactive,
                                 promotion=promotion,
                                 prospects=prospects,
                                 notonforums=notonforums,
                                 missingtitles=missingtitles,
                                 directroles=directroles
                                 )

@require_gradient(False)
def view_voters(environ):
    user = environ["emapps.user"]
    members = pickle.load(file(MEMBERFILE))
    voters = [name for name, details in members.items()
              if 'Employee' in details['titles']
              or 'Director' in details['titles']]
    voters.sort(lambda a, b: cmp(a.lower(), b.lower()))
    return kgi.template_response('gradient/voters.html',
                                 user=user,
                                 voters=voters)

@require_gradient(False)
def view_market(environ):
    user = environ["emapps.user"]
    table = []
    for (charname, staname, volentered, volremaining, minvolume, typename,
         range, wallet, duration, escrow,
         price, bid, issued) in list(csv.reader(file(MORDERFILE))):
        if int(bid) == 0:
            continue
        b = tempita.bunch()
        
        b.update({'pilot': charname,
                  'station': staname,
                  'volentered': int(volentered),
                  'volremaining': int(volremaining),
                  'minvolume': int(minvolume),
                  'typename': typename,
                  'range': int(range),
                  'wallet': wallet,
                  'duration': datetime.timedelta(days=int(duration)),
                  'escrow': escrow,
                  'price': float(price),
                  'bid': bid,
                  'issued': datetime.datetime.utcfromtimestamp(int(issued))})
        table.append(b)
    return kgi.template_response('gradient/marketorders.html',
                                 user=user,
                                 orders=table)
    
