import datetime

from django.conf import settings
from django.views.generic.simple import direct_to_template
from emtools import utils
from emtools.ccpeve.models import APIKey
from emtools.emauth.decorators import require_mybbgroup
import emtools.ccpeve.igb as igb

from collections import defaultdict

@require_mybbgroup(['Gradient Executive', 'Gradient Personnel Manager'])
def view_members(request):
    grd = APIKey.objects.get(name='Gradient').corp()
    ms = grd.MemberSecurity()
    mt = grd.MemberTracking(extended=1)
    pilots = {}
    for member in ms.members:
        pilots.setdefault(member.name, defaultdict(lambda: ""))
        pilots[member.name]['id'] = member.characterID
        pilots[member.name]['titles'] = [title.titleName
                                         for title in getattr(member,
                                                              'titles',
                                                              [])]
        pilots[member.name]['roles'] = [role.roleName
                                        for role in member.roles]
    for member in mt.members:
        pilots.setdefault(member.name, defaultdict(lambda: ""))
        pilots[member.name]['id'] = member.characterID
        pilots[member.name]['start'] = datetime.datetime.utcfromtimestamp(member.startDateTime)
        pilots[member.name]['base'] = member.base
        pilots[member.name]['freeformtitle'] = member.title
        pilots[member.name]['logon'] = datetime.datetime.utcfromtimestamp(member.logonDateTime)
        pilots[member.name]['logoff'] = datetime.datetime.utcfromtimestamp(member.logoffDateTime)
        pilots[member.name]['location'] = member.location
        pilots[member.name]['ship'] = member.shipType

    personnel_threads, intro_threads, grd_users = get_forum_details()
    roster = get_roster()

    for name in pilots:
        lname = name.lower()
        if lname in personnel_threads:
            tid, prefix = personnel_threads[lname]
            pilots[name]['tid'] = tid
            if prefix == 20:
                pilots[name]['canbepromoted'] = True
            else:
                pilots[name]['canbepromoted'] = False
        else:
            pilots[name]['tid'] = None
            pilots[name]['canbepromoted'] = False
        if lname in roster:
            pilots[name]['roster'] = True
        if lname in intro_threads:
            pilots[name]['intro_thread'] = True
        else:
            pilots[name]['intro_thread'] = False
        if lname in grd_users:
            pilots[name]['auth'] = True
        else:
            pilots[name]['auth'] = False

    prospect_count = 0
    norole_count = 0
    inactive_count = 0
    onleave_count = 0
    shift_count = {1: 0, 2: 0, 3: 0}
    noshift_count = 0

    now = datetime.datetime.utcnow()
    for name, details in pilots.items():
        details['showinfo'] = igb.ShowInfoCharacter(details['id'])
        if 'roleDirector' in details['roles']:
            details['titles'].append('Director')
        if 'Prospect' not in details['titles'] and 'Employee' not in details['titles'] and 'Director' not in details['titles']:
            if 'on leave' not in details['freeformtitle'].lower():
                details['noroles'] = True
                norole_count += 1
        else:
            details['noroles'] = False

        details['lastactive'] = (now - details.get('logoff', now)).days
        if 'on leave' in details['freeformtitle'].lower():
            details['onleave'] = True
            onleave_count += 1
        elif details['lastactive'] > 30:
            inactive_count += 1
        elif '1/R' in details['freeformtitle']:
            details['shift'] = 1
            shift_count[1] += 1
        elif '2/R' in details['freeformtitle']:
            details['shift'] = 2
            shift_count[2] += 1
        elif '3/R' in details['freeformtitle']:
            details['shift'] = 3
            shift_count[3] += 1
        else:
            noshift_count += 1
        start = details.get('start', datetime.datetime.utcnow())
        details['age'] = (now - start).days
        if 'Prospect' in details['titles']:
            details['prospect'] = True
            prospect_count += 1
            age = details['age']
            details['d30'] = age >= 30
            details['d60'] = age >= 60
            details['d120'] = age >= 120
        else:
            details['prospect'] = False
        if details['lastactive'] > 30 and 'on leave' not in details['freeformtitle'].lower() and not details['noroles']:
            details['inactive'] = True
        else:
            details['inactive'] = False

    pilots = pilots.items()
    pilots.sort(key=lambda a: a[0])
    return direct_to_template(request, 'grdpersonnel/members.html',
                              extra_context={
            'tab': 'members',
            'pilots': pilots,
            'cacheduntil': datetime.datetime.utcfromtimestamp(max(ms._meta.cachedUntil, mt._meta.cachedUntil)),
            'prospect_count': prospect_count,
            'norole_count': norole_count,
            'inactive_count': inactive_count,
            'shift_count': shift_count,
            'noshift_count': noshift_count,
            'onleave_count': onleave_count,
            })

def get_forum_details():
    db = utils.connect('emforum')
    c = db.cursor()
    c.execute("SELECT LOWER(subject), tid, prefix FROM mybb_threads "
              "WHERE fid IN (129, 130, 131)")
    personnel_threads = dict((subject, (tid, prefix))
                             for (subject, tid, prefix) in c.fetchall())
    c.execute("SELECT LOWER(u.username), COUNT(*) "
              "FROM mybb_threads t "
              "     INNER JOIN mybb_users u ON t.uid = u.uid "
              "WHERE t.fid = 123 "
              "GROUP BY LOWER(u.username)")
    intro_threads = dict(c.fetchall())
    c.execute("SELECT LOWER(username) "
              "FROM mybb_users "
              "WHERE CONCAT(',', usergroup, ',', additionalgroups, ',') "
              "LIKE '%,60,%'")
    grd_users = set(name for (name,) in c.fetchall())
    return personnel_threads, intro_threads, grd_users

import re
import urllib

def get_roster():
    try:
        u = urllib.urlopen("http://gradient:{password}@gradient.orava.org/wiki/Roster"
                           .format(password=settings.GRDWIKIPASSWORD))
        s = u.read()
        return [name.lower()
                for name in re.findall(r"<li> *(.*?)[ 0-9.]*\n", s)]
    except:
        return []

class Bag(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
