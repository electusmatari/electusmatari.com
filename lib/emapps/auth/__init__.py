# API authentication application
# Uses the EVE API to authenticate users, and adds/removes user groups
# in MyBB.

# Call /auth/check/?password=... regularly to kick old users.

import cgi
import csv
import datetime
import logging
import pickle

import kgi
import eveapi

from emapps.responses import unauthorized
from emapps.util import require_permission
from emapps.util import eve_time

STANDINGSFILE = "/home/forcer/Projects/old-emcom/ftp/data/em-standings.txt"
GRDFILE = "/home/forcer/Projects/old-emcom/ftp/data/grd-personnel.txt"

TITLES = {'Ulphus': 'Alliance Leader',

          'Arthur Black': 'Alliance Diplomat',
          'Challis Drant': 'Alliance Diplomat',
          'Reika Shimohira': 'Alliance Diplomat',

          # BIONE
          'keyran tyler': 'Council Member',
          'Livia Verheor': 'Council Member',
          # GRD
          'Elsebeth Rhiannon': 'Council Member',
          'Theron Gyrow': 'Council Member',
          # RE-AW
          'Evanda Char': 'Council Member',
          # 'KillJoy Tseng': 'Council Member',
          # SOERR
          'Gerrard DuNord': 'Council Member',
          # -WB-
          'Karagh': 'Council Member',
          'duch crystal': 'Council Member',
          }

# List of tuples.
# Element 1: This is the group which requires API authentication.
# Element 2: A list of corps/alliances that give access to this group.
# Element 3: If this is True, a user without API key will lose the group.
REQUIRES = [
    ('Electus Matari', ['Electus Matari', 'Lutinari Syndicate'], True),
    ('Lutinari Syndicate', ['Lutinari Syndicate'], True),
    ]

GRDGROUPS = ['Gradient',
             'Gradient Employee',
             'Gradient Executive',
             'Gradient Personnel Manager',
             'Gradient Recruiter']

# Password for the check CGI
CHECK_PASSWORD = '<REDACTED>'

PAGESIZE = 10

log = logging.getLogger('auth')

def authapp(environ, start_response):
    """
    Main application interface. Dispatch over pages.
    """
    URLCONF = [
        ('^/check/', view_check),
        ('^/update/', view_auth),
        ('^/faq/', view_faq),
        ('^/corp/', view_corp),
        ('^/channels/', view_channels),
        ('^/avatar/', view_updateavatar),
        ('^/', view_info),
    ]
    return kgi.dispatch(environ, start_response, URLCONF)

def view_info(environ):
    """
    Show authentication status.
    """
    user = environ["emapps.user"]
    if not user.is_authenticated():
        return kgi.html_response(
            unauthorized(user, 'You need to log in to the forums.')
            )
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("SELECT last_attempt, message, authenticated, disabled "
              "FROM auth_user WHERE username = %s LIMIT 1",
              (user.username,))
    if c.rowcount == 1:
        (last_attempt, message, authenticated, disabled) = c.fetchone()
    else:
        (last_attempt, message, authenticated, disabled) = (None, None,
                                                            None, None)
    return kgi.template_response('auth/info.html',
                                 user=user,
                                 last_attempt=last_attempt,
                                 message=message,
                                 authenticated=authenticated,
                                 disabled=disabled)

def view_auth(environ):
    """
    User authentication form. Update details.
    """
    user = environ["emapps.user"]
    if not user.is_authenticated():
        return kgi.html_response(
            unauthorized(user, 'You need to log in to the forums.')
            )
    if environ["REQUEST_METHOD"] == 'POST':
        form = cgi.FieldStorage()
        username = user.username
        userid = form.getfirst("userid", None)
        apikey = form.getfirst("apikey", None)
        if userid == '' or userid is None:
            (userid, apikey) = get_apikey(username)
        update_allies()
        try:
            update_user(username, userid, apikey)
        except Exception, e:
            return kgi.template_response('auth/error.html',
                                         user=user,
                                         error=str(e))
        return kgi.redirect_response('http://www.electusmatari.com/auth/')
    return kgi.template_response('auth/update.html',
                                 user=user)

def view_faq(environ):
    """
    Show the FAQ.
    """
    return kgi.template_response('auth/faq.html',
                                 user=environ['emapps.user'])

@require_permission('em')
def view_channels(environ):
    """
    Offer to join channels.
    """
    return kgi.template_response('auth/channels.html',
                                 user=environ["emapps.user"])

@require_permission('corpadmin')
def view_corp(environ):
    """
    Show the members of your corp.
    """
    user = environ["emapps.user"]
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("SELECT corp FROM auth_user "
              "WHERE username = %s AND authenticated = 1",
              user.username)
    if c.rowcount == 0:
        return kgi.template_response('auth/corp.html',
                                     user=environ['emapps.user'],
                                     error="You are not authenticated.")
    corpname = c.fetchone()[0]
    c.execute("SELECT username FROM auth_user "
              "WHERE corp = %s "
              " AND authenticated = 1 "
              "ORDER BY username ASC",
              corpname)
    apiusers = [x for (x,) in c.fetchall()]
    db2 = kgi.connect('dbforums')
    c2 = db2.cursor()
    c2.execute("SELECT username, usertitle FROM mybb_users "
               "WHERE CONCAT(',', usergroup, ',', additionalgroups, ',') "
               "      LIKE '%,56,%' "
               "ORDER BY username ASC")
    c2.execute("SELECT username, lastactive FROM mybb_users")
    active = dict((username, datetime.datetime.utcfromtimestamp(lastactive))
                  for (username, lastactive) in c2.fetchall())
    users = [(username, active[username], False)
             for username in apiusers]
    users.sort(lambda a, b: cmp(a[0].lower(), b[0].lower()))
    return kgi.template_response('auth/corp.html',
                                 user=user,
                                 corp=corpname,
                                 error=None,
                                 users=users,
                                 now=datetime.datetime.utcnow())

def view_updateavatar(environ):
    """
    Set the avatar to an img.eve.is address.
    """
    user = environ["emapps.user"]
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("SELECT corp FROM auth_user "
              "WHERE username = %s AND authenticated = 1",
              user.username)
    if c.rowcount == 0:
        return kgi.template_response('403.html',
                                     reason='Not authenticated.')
    api = eveapi.EVEAPIConnection()
    charids = api.eve.CharacterID(names=user.username)
    charid = None
    for char in charids.characters:
        charid = char.characterID
    if charid is None:
        return kgi.redirect_response('http://www.electusmatari.com/auth/')
    db = kgi.connect('dbforums')
    c = db.cursor()
    url = 'http://img.eve.is/serv.asp?s=64&c=%s' % charid
    c.execute("UPDATE mybb_users SET avatar = %s "
              "WHERE LOWER(username) = LOWER(%s)",
              (url, user.username))
    return kgi.redirect_response('http://www.electusmatari.com/auth/')

# @require_permission('admin')
def view_check(environ):
    """
    Check all users whether they still can access the forums.

    This paginates the users so it will only check PAGESIZE per
    request, in case the server kills us off early.
    """
    form = cgi.FieldStorage()
    password = form.getfirst("password", "")
    if password != CHECK_PASSWORD:
        return kgi.template_response('403.html', reason='Wrong password.')

    try:
        offset = int(form.getfirst("offset", "0"))
    except ValueError:
        offset = 0

    # Get the alliance list now. On API error, bail out - the API is
    # down then.
    try:
        global alliances
        api = eveapi.EVEAPIConnection()
        alliances = api.eve.AllianceList().alliances
    except Exception, e:
        log.error("Error getting the alliance list, check aborted: %s"
                  % (str(e),))
        return

    update_allies()

    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("SELECT COUNT(*) FROM auth_user WHERE disabled = 0")
    count = c.fetchone()[0]

    if offset < 0:
        offset = 0
    elif offset >= count:
        offset = count - 1
    nextoffset = offset + PAGESIZE

    c.execute("SELECT username, userid, apikey FROM auth_user "
              "WHERE disabled = 0 "
              "LIMIT %s OFFSET %s" %
              (PAGESIZE, offset))
    users = c.fetchall()
    for (username, userid, apikey) in users:
        try:
            # If we disable this user, the next offset will have to
            # start one early.
            if not update_user(username, userid, apikey):
                nextoffset -= 1
        except Exception, e:
            log.error("Error while updating %s: %s" % (username, str(e)))

    if nextoffset < count:
        return kgi.redirect_response('http://www.electusmatari.com/auth/check/?password=%s&offset=%s' %
                                     (password, nextoffset))

    log.info("Authenticated %i users." % (count - ((offset + PAGESIZE)
                                                   - nextoffset)))

    remove_users_without_api()
    return kgi.redirect_response('http://www.electusmatari.com/admin/')

def update_allies():
    # Update the REQUIRES list for allies
    allies = []
    for std in csv.reader(file(STANDINGSFILE)):
        if int(float(std[4])) == 10:
            allies.append(std[1])
    REQUIRES.append(('Ally', allies, False))

def remove_users_without_api():
    """
    Throw all users out of "our" groups that don't have configured API
    keys.
    """
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("SELECT username FROM auth_user")
    users = [x for (x,) in c.fetchall()]

    db = kgi.connect('dbforums')
    c = db.cursor()
    c.execute("SELECT gid FROM mybb_usergroups "
              "WHERE title IN (%s)" % ", ".join(["%s"]*len(REQUIRES + 
                                                           GRDGROUPS)),
              [groupname for (groupname, _, _) in REQUIRES] +
              GRDGROUPS)
    
    gids = ["%%,%s,%%" % x for (x,) in c.fetchall()]
    c.execute("SELECT username FROM mybb_users "
              "WHERE "
              +
              " OR ".join(["CONCAT(',', usergroup, ',', additionalgroups, ',')"
                           " LIKE %s"] * len(REQUIRES + GRDGROUPS)),
              gids)
    for (username,) in c.fetchall():
        if username not in users:
            user = MyBBUser(username)
            groups = ([groupname for (groupname, _, require_key)
                       in REQUIRES if require_key] +
                      GRDGROUPS)
            for groupname in groups:
                if user.has_group(groupname):
                    user.remove_group(groupname)
                    log.info("User %s loses group %s: No API key stored."
                             % (username, groupname))
            user.save()

def update_user(username, userid, apikey):
    """
    Check a single user and update his forum groups.
    """
    try:
        apiuser = APIUser(username, userid, apikey)
    except eveapi.Error, e:
        # Magic numbers ahoy. All numbers that indicate that the user
        # should lose access. Check
        # http://api.eveonline.com/eve/ErrorList.xml.aspx
        if e.code in (106, # Invalid userID
                      202,
                      203, # Invalid apiKey
                      204,
                      205,
                      210,
                      211, # Account expired
                      212):
            reason = ("API error %s: %s" % (e.code, str(e)))
            update_usergroups(username, [], ([groupname
                                              for (groupname, _, _)
                                              in REQUIRES] +
                                             GRDGROUPS),
                              reason)
            update_userdetails(username=username,
                               userid=userid, apikey=apikey, message=reason,
                               authenticated=0, disabled=1)
            return False
        else:
            raise
    except APIError, e:
        reason = ("Pilot %s not found on this account."
                  % username)
        update_usergroups(username, [], [groupname
                                         for (groupname, _, _)
                                         in REQUIRES] + GRDGROUPS,
                          reason)
        update_userdetails(username=username, userid=userid,
                           apikey=apikey, authenticated=0, disabled=1,
                           message=reason)
        return False
    add = set()
    remove = set()
    for (groupname, entities, _) in REQUIRES:
        gain = False
        for entity in entities:
            if apiuser.member_of(entity):
                gain = True
                break
        if gain:
            add.add(groupname)
        else:
            remove.add(groupname)
    if apiuser.member_of("Gradient"):
        gradientauth(username, add, remove)
    else:
        remove.update(GRDGROUPS)
    update_usergroups(username, add, remove)
    update_userdetails(username=username, userid=userid, apikey=apikey,
                       corp=apiuser.corp, alliance=apiuser.alliance,
                       message='API key is valid.', authenticated=1,
                       disabled=0)
    return True

_grdpersonnel = None
def gradientauth(username, add, remove):
    """
    Add Gradient groups to this api user.
    """
    global _grdpersonnel
    if _grdpersonnel is None:
        _grdpersonnel = pickle.load(file(GRDFILE))
    if username not in _grdpersonnel:
        remove.update(GRDGROUPS)
        return
    details = _grdpersonnel[username]
    add.add('Gradient')
    titles = details['titles']
    if 'Employee' in titles or 'Director' in titles:
        add.add('Gradient Employee')
    else:
        remove.add('Gradient Employee')
    if 'Director' in titles or 'Shift manager' in titles:
        add.add('Gradient Executive')
    else:
        remove.add('Gradient Executive')
    if 'Recruiter' in details['freeformtitle']:
        add.add('Gradient Recruiter')
    else:
        remove.add('Gradient Recruiter')
    if 'Recruiter' in titles or 'Director' in titles or 'Shift manager' in titles:
        add.add('Gradient Personnel Manager')
    else:
        remove.add('Gradient Personnel Manager')

def update_usergroups(username, add, remove, reason=False):
    """
    Update a single user.
    add is a list of groups to add.
    remove is a list of groups to remove.
    If reason is true, it's given in the log message as a reason for
    the change.
    """
    added = set()
    removed = set()
    try:
        user = MyBBUser(username)
    except RuntimeError:
        return
    for group in add:
        if not user.has_group(group):
            user.add_group(group)
            added.add(group)
    for group in remove:
        if user.has_group(group):
            user.remove_group(group)
            removed.add(group)
    user.save()    
    log_info(username, added, removed, reason)

def log_info(username, added, removed, reason):
    """
    Do a log entry for a usergroup change.
    """
    if len(added) > 0 or len(removed) > 0:
        message = "User %s" % username
        if len(added) > 0:
            if len(added) == 1:
                plural = "group"
            else:
                plural = "groups"
            message += " gained %s %s" % (plural,
                                          ", ".join(str(x) for x in added))
            if len(removed) > 0:
                message += " and"
        if len(removed) > 0:
            if len(removed) == 1:
                plural = "group"
            else:
                plural = "groups"
            message += " lost %s %s" % (plural,
                                        ", ".join(str(x) for x in removed))
        if reason:
            message += ": %s" % reason
        log.info(message)

def update_userdetails(username, userid, apikey, message, authenticated,
                       disabled, corp=None, alliance=None):
    """
    Update the user API key details.
    message is displayed to the user.
    authenticated is a boolean to check whether the API key is valid.
    disabled is a boolean saying whether to try authentication again.
    """
    db = kgi.connect('dbforcer')
    c = db.cursor()
    sql = ("UPDATE auth_user "
           "SET userid = %s, "
           "    apikey = %s, "
           "    message = %s, "
           "    authenticated = %s, "
           "    disabled = %s, ")
    args = [userid, apikey, message, authenticated, disabled]
    if corp is not None:
        sql += "    corp = %s, "
        args.append(corp)
        if alliance is not None:
            sql += "    alliance = %s, "
            args.append(alliance)
        else:
            sql += "    alliance = '', "
    sql += ("    last_attempt = NOW() "
            "WHERE username = %s")
    args.append(username)
    c.execute(sql, args)
    if c.rowcount == 0:
        c.execute("INSERT INTO auth_user (userid, apikey, message, "
                  "                       authenticated, disabled, "
                  "                       corp, alliance, "
                  "                       username, last_attempt) "
                  "VALUES (%s, %s, %s, "
                  "        %s, %s, "
                  "        %s, %s, "
                  "        %s, NOW())",
                  (userid, apikey, message,
                   authenticated, disabled,
                   corp, alliance,
                   username))

    if corp is not None:
        db2 = kgi.connect('dbforums')
        c2 = db2.cursor()
        if username in TITLES:
            usertitle = TITLES[username]
        elif alliance is None:
            usertitle = "%s" % corp
        else:
            usertitle = "%s<br />%s" % (corp, alliance)
        c2.execute("UPDATE mybb_users SET usertitle = %s "
                   "WHERE username = %s",
                   (usertitle, username))

def get_apikey(username):
    """
    Get the userid and apikey of a given user.
    """
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("SELECT userid, apikey FROM auth_user "
              "WHERE username = %s",
              (username,))
    return c.fetchone()

alliances = None

class APIError(Exception):
    pass

class APIUser(object):
    """
    An API user (account).
    Caches details and can be asked what corps/alliances the account
    is a member of.
    """
    def __init__(self, username, userid, apikey):
        self.userid = userid
        self.apikey = apikey
        self.name = None
        self.corp = None
        self.alliance = None
        api = eveapi.EVEAPIConnection().auth(userID=userid, apiKey=apikey)
        for char in api.account.Characters().characters:
            if char.name == 35:
                char.name = "0x23"
            if str(char.name).lower() == username.lower():
                self.name = str(char.name)
                self.corp = str(char.corporationName)
                self.alliance = get_corp_alliance(char.corporationID)
        if self.name is None:
            raise APIError, ("Pilot %s not found on this account"
                             % username)

    def member_of(self, name):
        """
        Return True iff the user is a member of this entity.
        """
        if name in [self.corp, self.alliance]:
            return True
        return False

def get_corp_alliance(corpid):
    """
    Return a list of alliances for a given corp ID.
    This caches the alliance list call.
    """
    global alliances
    if alliances is None:
        api = eveapi.EVEAPIConnection()
        alliances = api.eve.AllianceList().alliances
    for ally in alliances:
        for allycorp in ally.memberCorporations:
            if allycorp.corporationID == corpid:
                return ally.name
    return None

gid2group = None

class MyBBUser(object):
    """
    A MyBB forum user.

    Used to add and remove groups.
    """
    def __init__(self, username):
        self.username = username
        db = kgi.connect('dbforums')
        c = db.cursor()
        if gid2group is None:
            c.execute("SELECT title, gid FROM mybb_usergroups")
            global gid2group
            gid2group = dict(c.fetchall())
        c.execute("SELECT usergroup, additionalgroups FROM mybb_users "
                  "WHERE username = %s",
                  (username,))
        if c.rowcount == 0:
            log.error("User %s does not exist." % username)
            raise RuntimeError, "User does not exist"
        (usergroup, additionalgroups) = c.fetchone()
        self.groups = ([int(usergroup)]
                       + [int(x) for x in additionalgroups.split(",")
                          if x != ''])
        self.modified = False
    
    def has_group(self, groupname):
        """
        Returns True if the user is a member of that group.
        """
        return gid2group[groupname] in self.groups

    def add_group(self, groupname):
        """
        Adds a group to the user if he's not already in it.
        """
        gid = gid2group[groupname]
        if gid not in self.groups:
            self.modified = True
            self.groups.append(gid)

    def remove_group(self, groupname):
        """
        Removes a group from the user.
        """
        gid = gid2group[groupname]
        if gid in self.groups:
            self.modified = True
            self.groups.remove(gid)

    def save(self):
        """
        Save the new group memberships of this user.
        """
        if not self.modified:
            return
        if len(self.groups) > 0:
            (usergroup, additionalgroups) = (self.groups[0],
                                             self.groups[1:])
        else:
            (usergroup, additionalgroups) = (2, # Registered
                                             [])
        db = kgi.connect('dbforums')
        c = db.cursor()
        c.execute("UPDATE mybb_users "
                  "SET usergroup = %s, "
                  "    additionalgroups = %s "
                  "WHERE username = %s",
                  (usergroup,
                   ",".join(str(x) for x in additionalgroups),
                   self.username))

    
# CREATE TABLE auth_user (
#   id SERIAL NOT NULL,
#   username VARCHAR(255) NOT NULL,
#   userid VARCHAR(32) NOT NULL,
#   apikey VARCHAR(128) NOT NULL,
#   last_attempt TIMESTAMP NOT NULL,
#   message VARCHAR(255) NOT NULL,
#   authenticated BOOL NOT NULL,
#   disabled BOOL NOT NULL,
#   corp VARCHAR(255),
#   alliance VARCHAR(255)
# );
