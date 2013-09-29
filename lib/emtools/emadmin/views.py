import datetime

from django.contrib.auth.models import User
from django.db import connection
from django.views.generic.list_detail import object_list
from django.views.generic.simple import direct_to_template

from emtools.emauth.decorators import require_admin
from emtools.emadmin.models import LogRecord, Schedule

from emtools import utils

OLD_DAYS = 7

@require_admin
def view_log(request):
    return object_list(request, LogRecord.objects.all(),
                       paginate_by=23,
                       template_name='emadmin/log.html',
                       extra_context={'tab': 'log'},
                       template_object_name='log')

@require_admin
def view_status(request):
    return direct_to_template(request, 'emadmin/status.html',
                              extra_context={'tab': 'status',
                                             'schedule_list':
                                                 Schedule.objects.all()})

IGNORED_GROUPS = ['Registered', 'Awaiting Activation', 'Banned']

@require_admin
def view_groups(request):
    db = utils.connect('emforum')
    c = db.cursor()
    c.execute("SELECT gid, title FROM mybb_usergroups")
    gid2name = dict(c.fetchall())
    c.execute("SELECT uid, username, lastactive, usergroup, additionalgroups "
              "FROM mybb_users")
    group_users = {}
    now = datetime.datetime.utcnow()
    for (mybb_uid, mybb_username, lastactive,
         usergroup, additionalgroups) in c.fetchall():
        try:
            user = User.objects.get(profile__mybb_uid=mybb_uid)
        except User.DoesNotExist:
            user = None
        lastactive = datetime.datetime.utcfromtimestamp(lastactive)
        delta = now - lastactive
        gids = [usergroup] + [int(gid) for gid in additionalgroups.split(",")
                              if gid != '']
        for gid in gids:
            group = gid2name.get(gid, "<Group %i>" % gid)
            if group in IGNORED_GROUPS:
                continue
            group_users.setdefault(group, [])
            group_users[group].append({'name': mybb_username,
                                       'user': user,
                                       'lastactive': lastactive,
                                       'days': delta.days,
                                       'cssclass': ('veryold'
                                                    if delta.days > OLD_DAYS
                                                    else '')})
    for users in group_users.values():
        users.sort(lambda a, b: cmp(a['name'].lower(), b['name'].lower()))
    groups = [(name, len(users), users)
              for (name, users) in group_users.items()]
    groups.sort(lambda a, b: cmp(a[0].lower(), b[0].lower()))
    return direct_to_template(request, 'emadmin/groups.html',
                              extra_context={'tab': 'groups',
                                             'group_list': groups})

@require_admin
def view_stats(request):
    conn = utils.connect('emmisc')
    c = conn.cursor()
    c.execute("SELECT table_schema, "
              "       SUM(table_rows) AS rows, "
              "       SUM(data_length + index_length) AS size "
              "FROM information_schema.TABLES "
              "GROUP BY table_schema "
              "ORDER BY size DESC")
    mysql_databases = c.fetchall()
    c.execute("SELECT table_name, "
              "       table_rows AS rows, "
              "       data_length + index_length AS size "
              "FROM information_schema.TABLES "
              "ORDER BY size DESC")
    mysql_tables = c.fetchall()
    c = connection.cursor()
    c.execute("SELECT 'eve', "
              "       (SELECT SUM(n_live_tup) FROM pg_stat_all_tables), "
              "       pg_database_size('eve')")
    postgresql_databases = c.fetchall()
    c.execute("""
SELECT CASE WHEN nspname = 'public'
            THEN relname
            ELSE nspname || '.' || relname
       END AS "relation",
       C.reltuples::numeric AS rows,
       pg_total_relation_size(C.oid) AS "total_size"
  FROM pg_class C
  LEFT JOIN pg_namespace N ON (N.oid = C.relnamespace)
  WHERE nspname NOT IN ('pg_catalog', 'information_schema')
    AND C.relkind <> 'i'
    AND nspname !~ '^pg_toast'
  ORDER BY pg_total_relation_size(C.oid) DESC
""")
    postgresql_tables = c.fetchall()
    return direct_to_template(request, 'emadmin/stats.html',
                              extra_context={'tab': 'stats',
                                             'mysql_databases': mysql_databases,
                                             'mysql_tables': mysql_tables,
                                             'postgresql_databases': postgresql_databases,
                                             'postgresql_tables': postgresql_tables})
