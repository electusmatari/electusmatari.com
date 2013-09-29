import cgi
import datetime
import logging

import kgi
import eveapi

from emapps.util import require_permission
from emapps.util import eve_time

log = logging.getLogger('admin')

INTERNALGROUPS = ['Capitals', 'Council', 'Personnel Manager',
                  'Secure', 'Tournament']

def adminapp(environ, start_response):
    URLCONF = [
        ('^/permissions/', view_permissions),
        ('^/groups/', view_groups),
        ('^/api/', view_api),
        ('^/tinfoil/', view_tinfoil),
        ('^/combat/', view_combat),
        ('^/$', view_log),
    ]
    return kgi.dispatch(environ, start_response, URLCONF)

@require_permission('admin')
def view_permissions(environ):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    if environ['REQUEST_METHOD'] == 'POST':
        form = cgi.FieldStorage()
        action = form.getfirst('action', None)
        username = form.getfirst('username', None)
        permission = form.getfirst('permission', None)
        if None not in (action, username, permission):
            username = username.strip()
            permission = permission.strip()
            if action == 'add':
                log.info('%s added permission %s to user %s.' %
                         (environ['emapps.user'].username,
                          permission, username))
                c.execute("INSERT INTO userpermissions (username, permission) "
                          "VALUES (%s, %s)",
                          (username, permission))
            elif action == 'remove':
                log.info('%s removed permission %s from user %s.' %
                         (environ['emapps.user'].username,
                          permission, username))
                c.execute("DELETE FROM userpermissions WHERE username = %s "
                          "AND permission = %s",
                          (username, permission))
        return kgi.redirect_response('http://www.electusmatari.com/admin/permissions/')
    else:
        c.execute("SELECT username, permission FROM userpermissions "
                  "ORDER BY permission ASC, username ASC")
        return kgi.template_response('admin/users.html',
                                     user=environ["emapps.user"],
                                     current_time=eve_time(),
                                     permissions=kgi.fetchbunches(c))

@require_permission('admin')
def view_log(environ):
    page = kgi.paginate('log', dbname='dbforcer', extra='ORDER BY time DESC')

    return kgi.template_response('admin/log.html',
                                 user=environ['emapps.user'],
                                 current_time=eve_time(),
                                 log=page)

@require_permission('admin')
def view_groups(environ):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    db = kgi.connect('dbforums')
    c = db.cursor()
    c.execute("SELECT gid, title FROM mybb_usergroups WHERE type = 2")
    groupname = dict(c.fetchall())
    members = {}
    active = {}
    c.execute("SELECT username, usergroup, additionalgroups, lastactive "
              "FROM mybb_users")
    for (username, usergroup, agroups, lastactive) in c.fetchall():
        active[username] = datetime.datetime.utcfromtimestamp(lastactive)
        for gid in ([usergroup] + agroups.split(",")):
            if gid != '' and int(gid) in groupname:
                group = groupname[int(gid)]
                if group not in members:
                    members[group] = {}
                members[group][username] = True
    groups = groupname.values()
    groups.sort(lambda a, b: cmp(a.lower(), b.lower()))
    result = []
    for group in groups:
        users = members.get(group, {}).keys()
        users.sort(lambda a, b: cmp(a.lower(), b.lower()))
        result.append((group, users))

    form = cgi.FieldStorage()
    if form.getfirst('format', None) == 'csv':
        import StringIO
        import csv
        out_port = StringIO.StringIO()
        out = csv.writer(out_port)
        for (group, users) in result:
            for user in users:
                out.writerow([group, user, str(active[user])])
        out_port.seek(0)
        return kgi.html_response(out_port.read(),
                                 header=[('Content-Type', 'text/plain')])

    badgroups = {}
    for group in members:
        if group in INTERNALGROUPS:
            for username in members[group]:
                if (username not in members.get('Electus Matari', [])
                    and username not in members.get('Tin Foil', [])):
                    badgroups.setdefault(group, [])
                    badgroups[group].append(username)
        
    return kgi.template_response('admin/groups.html',
                                 user=environ['emapps.user'],
                                 groups=result,
                                 badgroups=badgroups.items(),
                                 active=active,
                                 now=datetime.datetime.utcnow())

@require_permission('admin')
def view_api(environ):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("SELECT username, corp, alliance "
              "FROM auth_user "
              "WHERE disabled = 0 "
              "ORDER BY alliance, corp, username ASC")
    alliances = {}
    for (user, corp, alliance) in c.fetchall():
        if alliance not in alliances:
            alliances[alliance] = {}
        if corp not in alliances[alliance]:
            alliances[alliance][corp] = []
        alliances[alliance][corp].append(user)
    db2 = kgi.connect('dbforums')
    c2 = db2.cursor()
    c2.execute("SELECT username, lastactive FROM mybb_users")
    active = dict((username, datetime.datetime.utcfromtimestamp(lastactive))
                  for (username, lastactive) in c2.fetchall())
    return kgi.template_response('admin/api.html',
                                 user=environ["emapps.user"],
                                 current_time=eve_time(),
                                 alliances=alliances,
                                 active=active,
                                 now=datetime.datetime.utcnow())

def view_tinfoil(environ):
    db = kgi.connect('dbforums')
    c = db.cursor()
    c.execute("SELECT username, usertitle, lastactive FROM mybb_users "
              "WHERE CONCAT(',', usergroup, ',', additionalgroups, ',') "
              "      LIKE '%,56,%' "
              "ORDER BY username ASC")
    emusers = c.fetchall()
    emusernames = [user for (user, _, _) in emusers]
    c.execute("SELECT username, usertitle, lastactive FROM mybb_users "
              "WHERE CONCAT(',', usergroup, ',', additionalgroups, ',') "
              "      LIKE '%,65,%' "
              "ORDER BY username ASC")
    grdusers = c.fetchall()
    grdusernames = [user for (user, _, _) in grdusers]
    
    usernames = emusernames + grdusernames
    api = eveapi.EVEAPIConnection()
    mapping = dict((x.name.lower(), x.characterID) for x in
                   api.eve.CharacterID(names=",".join(usernames)).characters)
    emusers = [(user,
                mapping.get(user.lower(), 0),
                title,
                datetime.datetime.utcfromtimestamp(lastactive))
               for (user, title, lastactive)
               in emusers]
    grdusers = [(user,
                 mapping.get(user.lower(), 0),
                 title,
                 datetime.datetime.utcfromtimestamp(lastactive))
                for (user, title, lastactive)
                in grdusers]
    return kgi.template_response('admin/tinfoil.html',
                                 user=environ["emapps.user"],
                                 now=datetime.datetime.utcnow(),
                                 emusers=emusers,
                                 grdusers=grdusers)

@require_permission('admin')
def view_combat(environ):
    startnow = datetime.datetime.utcnow()
    if startnow.month == 12:
        endnow = datetime.datetime(year=startnow.year+1, month=1, day=1)
    else:
        endnow = datetime.datetime(year=startnow.year, month=startnow.month+1,
                                   day=1)
    form = cgi.FieldStorage()
    startyear = int(form.getfirst('startyear', startnow.year))
    startmonth = int(form.getfirst('startmonth', startnow.month))
    endyear = int(form.getfirst('endyear', endnow.year))
    endmonth = int(form.getfirst('endmonth', endnow.month))
    active_all = get_active(startyear, startmonth, endyear, endmonth,
                            0, 24)
    active_1st = get_active(startyear, startmonth, endyear, endmonth,
                            6, 14)
    active_2nd = get_active(startyear, startmonth, endyear, endmonth,
                            14, 22)
    active_3rd = get_active(startyear, startmonth, endyear, endmonth,
                            22, 06)
    return kgi.template_response('admin/combat.html',
                                 user=environ["emapps.user"],
                                 now=datetime.datetime.utcnow(),
                                 active_list=[("All Day", active_all),
                                              ("1st Shift", active_1st),
                                              ("2nd Shift", active_2nd),
                                              ("3rd Shift", active_3rd)],
                                 startyear=startyear,
                                 startmonth=startmonth,
                                 endyear=endyear,
                                 endmonth=endmonth)

def get_active(startyear, startmonth, endyear, endmonth, starthour, endhour):
    db = kgi.connect('dbkillboard')
    c = db.cursor()
    if endhour > starthour:
        hoursql = ("  AND HOUR(k.kll_timestamp) >= %%s "
                   "  AND HOUR(k.kll_timestamp) < %%s ")
        args = [starthour, endhour]
    else:
        hoursql = ("  AND (HOUR(k.kll_timestamp) >= %%s "
                   "       OR HOUR(k.kll_timestamp) < %%s) ")
        args = [starthour, endhour]
    c.execute(("SELECT c.crp_name, COUNT(*) AS kcount "
               "FROM kb3_inv_detail d "
               "     INNER JOIN kb3_kills k "
               "       ON d.ind_kll_id = k.kll_id "
               "     INNER JOIN kb3_corps c "
               "       ON d.ind_crp_id = c.crp_id "
               "     INNER JOIN kb3_alliances a "
               "       ON d.ind_all_id = a.all_id "
               "WHERE k.kll_timestamp >= '%04i-%02i' "
               "  AND k.kll_timestamp < '%04i-%02i' "
               + hoursql +
               "  AND a.all_name = 'Electus Matari' "
               "GROUP BY d.ind_crp_id "
               "ORDER BY kcount DESC") % (startyear, startmonth,
                                          endyear, endmonth),
              tuple(args))
    involved_corps = dict(c.fetchall())
    c.execute(("SELECT c.crp_name, d.ind_plt_id, COUNT(*) AS killcount "
               "FROM kb3_inv_detail d "
               "     INNER JOIN kb3_kills k "
               "       ON d.ind_kll_id = k.kll_id "
               "     INNER JOIN kb3_corps c "
               "       ON d.ind_crp_id = c.crp_id "
               "     INNER JOIN kb3_alliances a "
               "       ON d.ind_all_id = a.all_id "
               "WHERE k.kll_timestamp >= '%04i-%02i' "
               "  AND k.kll_timestamp < '%04i-%02i' "
               + hoursql +
               "  AND a.all_name = 'Electus Matari' "
               "GROUP BY c.crp_name, d.ind_plt_id") % (startyear, startmonth,
                                                       endyear, endmonth),
              tuple(args))
    active = {}
    for (corp, pilot, killcount) in c.fetchall():
        if corp not in active:
            active[corp] = (0, 0)
        (multi, single) = active[corp]
        if killcount > 1:
            multi += 1
        else:
            single += 1
        active[corp] = (multi, single)
    active = [(corp, multi, single, involved_corps.get(corp, 0))
              for (corp, (multi, single))
              in active.items()]
    active.sort()
    return active
