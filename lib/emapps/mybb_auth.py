import kgi
import Cookie

forum_names = { 'em': "Internal", 'grd': "<span class=\"grdmainforum\">Gradient</span>" }

def mybb_auth(environ):
    cookie = Cookie.SimpleCookie(environ.get("HTTP_COOKIE"))
    try:
        (uid, loginkey) = cookie["mybbuser"].value.split("_", 1)
    except KeyError:
        return ("Anonymous", False)
    except ValueError:
        return ("Anonymous", False)

    db = kgi.connect('dbforums')
    c = db.cursor()
    c.execute("""SELECT username, usergroup, additionalgroups
                 FROM mybb_users
                 WHERE uid=%s AND loginkey=%s
                 LIMIT 1
              """, (uid, loginkey))
    if c.rowcount < 1:
        return ("Anonymous", False)
    (username, usergroup, additionalgroups) = c.fetchone()
    groups = [int(usergroup)]
    if additionalgroups != '':
        groups.extend([int(x) for x in additionalgroups.split(",")])

    groupexpr = ",".join(["%s"]*len(groups))

    auth_flags = {}
    for auth_group in forum_names:
        c.execute("""
              SELECT COUNT(*)
              FROM mybb_forums AS forums
                   INNER JOIN mybb_forumpermissions AS perm
                     ON forums.fid = perm.fid
              WHERE forums.name = %%s
                AND perm.gid IN (%s)
                AND perm.canview = 1;
              """ % groupexpr,
              tuple([forum_names[auth_group]] + groups))
        count = c.fetchone()[0]
        auth_flags[auth_group] = count > 0

    return (username, auth_flags)
