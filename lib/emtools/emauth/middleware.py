from django.contrib.auth.models import User, AnonymousUser

from emtools import utils
from emtools.emauth.models import Profile

class MyBBAuthenticationMiddleware(object):
    def process_request(self, request):
        auth = mybb_auth(request)
        if auth is None:
            request.user = AnonymousUser()
            return
        uid, username, groups = auth
        user, created = User.objects.get_or_create(profile__mybb_uid=uid,
                                                   defaults={'username':
                                                                 "mybb%s" %
                                                                   uid})
        if created:
            Profile.objects.create(user=user,
                                   mybb_uid=uid,
                                   mybb_username=username)
        user.profile.mybb_groups = groups
        if user.profile.mybb_username != username:
            user.profile.mybb_username = username
            user.save()

        request.user = user

def mybb_auth(request):
    cookie = request.COOKIES.get('mybbuser', None)
    if cookie is None:
        return None
    try:
        (uid, loginkey) = cookie.split("_", 1)
    except KeyError:
        return None
    except ValueError:
        return None

    conn = utils.connect('emforum')
    c = conn.cursor()
    c.execute("""SELECT username, usergroup, additionalgroups
                 FROM mybb_users
                 WHERE uid=%s AND loginkey=%s
                 LIMIT 1
              """, (uid, loginkey))
    if c.rowcount < 1:
        return None
    (username, usergroup, additionalgroups) = c.fetchone()
    groups = [int(usergroup)]
    if additionalgroups != '':
        groups.extend([int(x) for x in additionalgroups.split(",")])

    c.execute("SELECT title FROM mybb_usergroups "
              "WHERE gid IN (%s)" % ", ".join(["%s"]*len(groups)),
              groups)
    return (uid, username, [name for (name,) in c.fetchall()])
