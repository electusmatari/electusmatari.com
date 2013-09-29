import datetime

import logging

from emtools import utils
from emtools.emauth.models import Profile, AuthLog
from emtools.ccpeve.models import apiroot, APIKey
from emtools.ccpeve import eveapi

# Automatically authenticated groups
GUARDED_GROUPS = ['Ally',
                  'Electus Matari',
                  'Gradient',
                  'Gradient Employee',
                  'Gradient Executive',
                  'Gradient Recruiter',
                  'Gradient Personnel Manager',
                  'Lutinari Syndicate',
                  ]

# Remove members of the former group if they lack the latter.
SECURE_GROUPS = [('Council', 'Electus Matari'),
                 ('Secure', 'Electus Matari'),
                 ('Personnel Manager', 'Electus Matari'),
                 ('Capitals', 'Electus Matari'),
                 ('Diplomats', 'Electus Matari'),
                 ('Tournament', 'Electus Matari'),
                 ('Lutinari Directors', 'Lutinari Syndicate'),
                 ('Lutinari Recruiters', 'Lutinari Syndicate'),
                 ('Lutinari Members', 'Lutinari Syndicate'),
                 ]

log = logging.getLogger('auth')

def authenticate_users(user=None):
    """
    Authenticate all users.

    Go through MyBB users. If they do not have a profile, drop groups.
    If they have a profile, if it's not active, drop groups.
    Go through groups.
    """
    start = datetime.datetime.utcnow()
    db = utils.connect('emforum')

    # dict of name -> (titles, freeformtitle)
    grddetails = get_gradient_details()
    # set of entityID
    allies = get_allies()

    if user is None:
        users = get_mybbusers(db)
    else:
        users = get_mybbusers(db, user.profile.mybb_uid)

    api = apiroot()
    totalcount = 0
    activecount = 0

    for mybbuser in users:
        if mybbuser.has_group('Banned'):
            continue
        totalcount += 1
        oldcorp = None
        if mybbuser.profile:
            oldcorp = mybbuser.profile.corp
        reason = update_single_user(api, mybbuser, grddetails, allies)
        if len(mybbuser.toadd) == 0:
            active = False
        else:
            active = True
            activecount += 1
        if mybbuser.profile:
            if mybbuser.profile.usertitle:
                usertitle = '<b>%s</b><br />' % mybbuser.profile.usertitle
            elif mybbuser.has_group('Council'):
                usertitle = '<b>Council Member</b><br />'
            elif mybbuser.has_group('Diplomats'):
                usertitle = '<b>Alliance Diplomat</b><br />'
            else:
                usertitle = ''
            if mybbuser.profile.alliance:
                usertitle += '%s<br />%s' % (mybbuser.profile.corp,
                                             mybbuser.profile.alliance)
            elif mybbuser.profile.corp:
                usertitle += mybbuser.profile.corp
            mybbuser.usertitle = usertitle
        mybbuser.save()
        if mybbuser.profile:
            mybbuser.profile.active = active
            mybbuser.profile.save()
            newcorp = mybbuser.profile.corp
        change_description = mybbuser.change_description()
        if change_description is not None:
            message = "User %s %s: %s" % (mybbuser.username,
                                          change_description,
                                          reason)
            if not active:
                message += ", marking inactive"
            log.info("%s" % (message,))
            if mybbuser.profile:
                for corp in set([oldcorp, newcorp]):
                    if corp is not None:
                        AuthLog.objects.create(corp=corp, message=message)
            else:
                AuthLog.objects.create(corp=None, message=message)
    db.commit()
    end = datetime.datetime.utcnow()
    if user is None:
        log.info("Authenticated %i active users of %i in %s" %
                 (activecount, totalcount, str(end - start)))

def update_single_user(api, mybbuser, grddetails, allies):
    reason = update_single_user2(api, mybbuser, grddetails, allies)
    # Remove dependent groups
    for group, required in SECURE_GROUPS:
        if not mybbuser.gains_group(required):
            mybbuser.remove_group(group)
    return reason

def update_single_user2(api, mybbuser, grddetails, allies):
    for group in GUARDED_GROUPS:
        if not grddetails and group.startswith("Gradient"):
            continue
        mybbuser.remove_group(group)

    if mybbuser.profile is None:
        return "No profile stored"
    if mybbuser.profile.characterid is None:
        return "Not authenticated"

    if mybbuser.profile.mybb_username == 'Rus Rhiannon':
        # Ugly workaround, as the API raises an internal server error
        # when queried for a DUST soldier (as of 2013-08-10)
        mybbuser.add_group("Gradient Employee")
        mybbuser.add_group("Gradient Personnel Manager")
        return ("DUST Soldier")

    if not mybbuser.profile.active:
        return "Inactive account"

    profile = mybbuser.profile

    try:
        info = api.eve.CharacterInfo(characterID=profile.characterid)
    except eveapi.Error as e:
        if e.code == 522: # Failed getting character information.
            return "%s (character deleted?)" % str(e)
        raise AuthenticationError("Error during API call: %s" % str(e))
    except Exception as e:
        raise AuthenticationError("Error during API call: %s" % str(e))

    if hasattr(info, 'alliance'):
        info_alliance = info.alliance
        info_allianceID = info.allianceID
    else:
        info_alliance = None
        info_allianceID = None

    if profile.corp != info.corporation or profile.alliance != info_alliance:
        success_reason = ("Changed from %s, %s to %s, %s" %
                          (profile.corp, profile.alliance,
                           info.corporation, info_alliance))
    else:
        success_reason = ("Corp %s, alliance %s" %
                          (info.corporation, info_alliance))

    profile.mybb_username = mybbuser.username
    profile.name = info.characterName
    profile.characterid = info.characterID
    profile.corp = info.corporation
    profile.corpid = info.corporationID
    profile.alliance = info_alliance
    profile.allianceid = info_allianceID
    profile.last_check = datetime.datetime.utcnow()
    profile.save()

    # EM members
    if profile.alliance == 'Electus Matari':
        mybbuser.add_group('Electus Matari')

    # Allies
    if profile.allianceid in allies or profile.corpid in allies:
        mybbuser.add_group('Ally')

    # GRD members
    if profile.corp == 'Gradient':
        mybbuser.add_group('Gradient')
        if grddetails:
            grdauth(mybbuser, grddetails)

    # LUTI members
    if profile.corp == 'Lutinari Syndicate':
        mybbuser.add_group('Lutinari Syndicate')

    return success_reason

def grdauth(mybbuser, grddetails):
    (titles, freeform) = grddetails.get(mybbuser.profile.name, (None, None))
    if titles is None:
        return
    if 'Employee' in titles or 'Director' in titles:
        mybbuser.add_group('Gradient Employee')
    if 'Director' in titles or 'Shift manager' in titles:
        mybbuser.add_group('Gradient Executive')
    if 'Recruiter' in titles or 'Director' in titles or 'Shift manager' in titles:
        mybbuser.add_group('Gradient Personnel Manager')

def get_gradient_details():
    """
    Return a mapping of {username: (titleset, freeformtitle)}
    """
    grd = APIKey.objects.get(name='Gradient').corp()
    result = {}
    membertracking = grd.MemberTracking()
    for member in membertracking.members:
        result.setdefault(member.name, (set(), ''))
        (titles, freeform) = result[member.name]
        result[member.name] = (titles, member.title)
    try:
        membersecurity = grd.MemberSecurity()
    except Exception as e:
        logging.info("corp.MemberSecurity exception: %s" % str(e))
        return False
    for member in membersecurity.members:
        result.setdefault(member.name, (set(), ''))
        for role in member.roles:
            if role.roleName == 'roleDirector':
                result[member.name][0].add('Director')
        for title in getattr(member, 'titles', []):
            result[member.name][0].add(title.titleName)
    return result

def get_allies():
    allies = set()
    grd = APIKey.objects.get(name='Gradient').corp()
    try:
        contacts = grd.ContactList()
    except Exception as e:
        raise AuthenticationError("Error during API call: %s" % str(e))
    for contact in contacts.allianceContactList:
        if contact.standing == 10:
            allies.add(contact.contactID)
    return allies

def get_mybbusers(db, uid=None):
    c = db.cursor()
    if uid is None:
        usermap = dict((profile.mybb_uid, profile) for profile in
                       Profile.objects.all())
        c.execute("SELECT uid, username, "
                  "       usergroup, additionalgroups, displaygroup, "
                  "       usertitle "
                  "FROM mybb_users "
                  "ORDER BY username ASC")
    else:
        usermap = dict((profile.mybb_uid, profile) for profile in
                       Profile.objects.filter(mybb_uid=uid))
        c.execute("SELECT uid, username, "
                  "       usergroup, additionalgroups, displaygroup, "
                  "       usertitle "
                  "FROM mybb_users "
                  "WHERE uid = %s "
                  "ORDER BY username ASC",
                  (uid,))
    result = []
    for (uid, username, usergroup, additionalgroups, displaygroup,
         usertitle) in c.fetchall():
        result.append(MyBBUser(db, usermap.get(uid, None),
                               uid, username,
                               usergroup, additionalgroups, displaygroup,
                               usertitle))
    return result

def mybb_setavatar(c, uid, url, x, y):
    c.execute("UPDATE mybb_users "
              "SET avatar = %s, "
              "    avatardimensions = %s, "
              "    avatartype = 'remote' "
              "WHERE uid = %s",
              (url, "%s|%s" % (x, y), uid))

def mybb_setusername(c, uid, name):
    c.execute("SELECT uid FROM mybb_users WHERE username = %s",
              (name,))
    if c.rowcount != 0:
        return False
    c.execute("UPDATE mybb_users "
              "SET username = %s "
              "WHERE uid = %s",
              (name, uid))
    return True

class MyBBUser(object):
    DEFAULTGROUP = 2

    def __init__(self, db, profile, uid, username,
                 usergroup, additionalgroups, displaygroup, usertitle):
        self.db = db
        self.profile = profile
        self.uid = uid
        self.username = username
        self.usergroup = usergroup
        self.orig_usergroup = usergroup
        self.additionalgroups = additionalgroups
        self.orig_additionalgroups = additionalgroups
        self.displaygroup = displaygroup
        self.orig_displaygroup = displaygroup
        if usertitle is None:
            usertitle = ""
        self.usertitle = usertitle
        self.orig_usertitle = usertitle
        self.toadd = set()
        self.toremove = set()
        self.gained = []
        self.lost = []
        self._groups = None

    def save(self):
        self.finalize_groups()
        if (self.usergroup == self.orig_usergroup and
            self.additionalgroups == self.orig_additionalgroups and
            self.displaygroup == self.orig_displaygroup and
            self.usertitle == self.orig_usergroup):
            return
        c = self.db.cursor()
        c.execute("UPDATE mybb_users "
                  "SET usergroup = %s, "
                  "    additionalgroups = %s, "
                  "    displaygroup = %s, "
                  "    usertitle = %s "
                  "WHERE uid = %s",
                  (self.usergroup, self.additionalgroups, self.displaygroup,
                   self.usertitle, self.uid))

    def add_group(self, groupname):
        self.toadd.add(groupname)
        if groupname in self.toremove:
            self.toremove.remove(groupname)

    def remove_group(self, groupname):
        if groupname in self.toadd:
            self.toadd.remove(groupname)
        self.toremove.add(groupname)

    def finalize_groups(self):
        c = self.db.cursor()
        c.execute("SELECT title, gid FROM mybb_usergroups")
        group2gid = dict(c.fetchall())
        gids = ([self.usergroup] +
                [int(x) for x in self.additionalgroups.split(",") if x != ''])
        for groupname in self.toremove:
            gid = group2gid[groupname]
            if gid in gids:
                gids.remove(gid)
                self.lost.append(groupname)
        for groupname in self.toadd:
            gid = group2gid[groupname]
            if gid not in gids:
                gids.append(gid)
                self.gained.append(groupname)
        if len(gids) == 0:
            gids = [self.DEFAULTGROUP]
        self.displaygroup = 0
        self.usergroup = gids[0]
        self.additionalgroups = ",".join(str(x) for x in gids[1:])
        self.toadd = set()
        self.toremove = set()

    def change_description(self):
        message = ""
        if len(self.gained) > 0:
            self.gained.sort()
            message += ("gained %s %s" %
                        ("group" if len(self.gained) == 1 else "groups",
                         ", ".join(self.gained)))
        if len(self.lost) > 0:
            if len(self.gained) > 0:
                message += " and "
            self.lost.sort()
            message += ("lost %s %s" %
                        ("group" if len(self.lost) == 1 else "groups",
                         ", ".join(self.lost)))
        if message == '':
            return None
        else:
            return message

    def gains_group(self, groupname):
        return groupname in self.toadd

    def has_group(self, groupname):
        if self.gains_group(groupname):
            return True
        if self._groups is None:
            c = self.db.cursor()
            c.execute("SELECT gid, title FROM mybb_usergroups")
            gid2group = dict(c.fetchall())
            gids = ([self.usergroup] +
                    [int(x) for x in self.additionalgroups.split(",")
                     if x != ''])
            self._groups = [gid2group[gid] for gid in gids]
        return groupname in self._groups

class AuthenticationError(Exception):
    pass
