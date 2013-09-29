import datetime
import json

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic.simple import direct_to_template
from django.views.generic.list_detail import object_list

from emtools import utils
from emtools.emauth.decorators import require_mybbgroup
from emtools.emauth.models import Profile, AuthLog
from emtools.emauth.forms import APIKeyForm
from emtools.ccpeve.models import apiroot, APIKey

PERSONNEL = ['Personnel Manager', 'Council', 'Gradient Personnel Manager']

@require_mybbgroup(PERSONNEL)
def view_authlog(request):
    if request.user.is_staff:
        queryset = AuthLog.objects.all()
    else:
        queryset = AuthLog.objects.filter(corp=request.user.profile.corp)
    return object_list(request, queryset,
                       paginate_by=23,
                       template_name='corpadmin/log.html',
                       extra_context={'tab': 'log'},
                       template_object_name='log')

@require_mybbgroup(PERSONNEL)
def view_apiconfig(request):
    try:
        apikey = APIKey.objects.get(name=request.user.profile.corp)
    except APIKey.DoesNotExist:
        apikey = None
    if request.method == 'POST':
        form = APIKeyForm(request.POST)
        if form.is_valid():
            if apikey is not None:
                apikey.keyid = form.cleaned_data['keyid']
                apikey.vcode = form.cleaned_data['vcode']
                apikey.active = True
                apikey.save()
            else:
                APIKey.objects.create(
                    name=request.user.profile.corp,
                    keyid=form.cleaned_data['keyid'],
                    vcode=form.cleaned_data['vcode'],
                    characterid=request.user.profile.characterid,
                    active=True,
                    message="",
                    last_attempt=datetime.datetime.utcnow())
            messages.add_message(request, messages.INFO,
                                 "Corp API details updated.")
            return HttpResponseRedirect('/corpadmin/apiconfig/')
    else:
        form = APIKeyForm()
    return direct_to_template(request, 'corpadmin/apiconfig.html',
                              extra_context={'form': form,
                                             'apikey': apikey,
                                             'tab': 'apiconfig'})

@require_mybbgroup(PERSONNEL)
def view_members(request):
    if request.user.is_staff:
        queryset = Profile.objects.filter(active=True)
    else:
        queryset = Profile.objects.filter(corp=request.user.profile.corp,
                                          active=True)

    do_all = request.GET.get('do_all', False)
    oldforum = intval(request.GET.get('oldforum', 7))
    oldkb = intval(request.GET.get('oldkb', 28))
    oldapi = intval(request.GET.get('oldapi', 28))
    corplist = CorpList(do_all, oldforum, oldkb, oldapi)

    for member in queryset:
        corplist.add(member)
    corplist.finalize()

    return direct_to_template(request, 'corpadmin/members.html',
                              extra_context={'tab': 'members',
                                             'corp_list': corplist})

@require_mybbgroup(PERSONNEL)
def view_activity(request):
    # Corp restriction
    if request.user.is_staff:
        if "corpname" in request.GET:
            corp = request.GET["corpname"]
        else:
            corp = "Electus Matari"
    else:
        corp = request.user.profile.corp
    # Date restriction
    if "todate" in request.GET and request.GET["todate"] != '':
        try:
            todate = datetime.datetime.strptime(request.GET["todate"],
                                                "%Y-%m-%d")
        except ValueError:
            todate = datetime.datetime.utcnow()
            messages.add_message(request, messages.ERROR,
                                 "To date %s is malformed, should be "
                                 "YYYY-MM-DD." % request.GET["todate"])
    else:
        todate = datetime.datetime.utcnow()
    if "fromdate" in request.GET and request.GET["fromdate"] != '':
        try:
            fromdate = datetime.datetime.strptime(request.GET["fromdate"],
                                                  "%Y-%m-%d")
        except ValueError:
            fromdate = todate - datetime.timedelta(days=28)
            messages.add_message(request, messages.ERROR,
                                 "From date %s is malformed, should be "
                                 "YYYY-MM-DD." % request.GET["fromdate"])
    else:
        fromdate = todate - datetime.timedelta(days=28)
    todate = todate.replace(hour=0, minute=0, second=0, microsecond=0)
    fromdate = fromdate.replace(hour=0, minute=0, second=0, microsecond=0)
    # Actual data
    db = utils.connect("emkillboard")
    c = db.cursor()
    c.execute("SELECT HOUR(k.kll_timestamp), p.plt_name "
              "FROM kb3_kills k "
              "     INNER JOIN kb3_inv_detail inv ON k.kll_id = inv.ind_kll_id "
              "     INNER JOIN kb3_alliances a ON inv.ind_all_id = a.all_id "
              "     INNER JOIN kb3_corps c ON inv.ind_crp_id = c.crp_id "
              "     INNER JOIN kb3_pilots p ON inv.ind_plt_id = p.plt_id "
              "WHERE k.kll_timestamp >= %s "
              "  AND k.kll_timestamp < %s "
              "  AND (a.all_name = %s OR c.crp_name = %s)",
              (fromdate, todate, corp, corp))
    kbcount = {}
    for hour, name in c:
        kbcount.setdefault(hour, set())
        kbcount[hour].add(name)
    killboarddata = [(hour, len(pilots)) for (hour, pilots) in kbcount.items()]
    killboarddata.sort()
    # forumdata
    wanted_uids = [x.mybb_uid for x in
                   Profile.objects.filter(Q(active=True) &
                                          (Q(corp=corp) |
                                           Q(alliance=corp)))]
    if len(wanted_uids) == 0:
        forumdata = []
    else:
        db = utils.connect("emforum")
        c = db.cursor()
        c.execute("SELECT hour, COUNT(*) "
                  "FROM (SELECT DISTINCT HOUR(access) AS hour, uid "
                  "      FROM user_log "
                  "      WHERE access >= %%s "
                  "        AND access < %%s "
                  "        AND uid IN (%s) "
                  "     ) AS sq "
                  "GROUP BY hour" % ", ".join(["%s"] * len(wanted_uids)),
                  [fromdate, todate] + wanted_uids)
        # Displace by 0.5 to put it next to the killboard bars
        forumdata = [(hour + 0.5, count) for (hour, count) in c.fetchall()]
    return direct_to_template(request, 'corpadmin/activity.html',
                              extra_context={'tab': 'activity',
                                             'corpname': corp,
                                             'is_staff': request.user.is_staff,
                                             'fromdate': fromdate.strftime("%Y-%m-%d"),
                                             'todate': todate.strftime("%Y-%m-%d"),
                                             'killboarddata': json.dumps(killboarddata),
                                             'forumdata': json.dumps(forumdata)})
    
@require_mybbgroup(PERSONNEL)
def view_ajax(request):
    term = request.GET.get("term", "").lower()
    result = set()
    for profile in Profile.objects.filter(active=True):
        if profile.corp is not None and term in profile.corp.lower():
            result.add(profile.corp)
        if profile.alliance is not None and term in profile.alliance.lower():
            result.add(profile.alliance)
    result = [{'label': name, 'value': name} for name in result
              if name is not None]
    result.sort(lambda a, b: cmp(a['label'].lower(), b['label'].lower()))
    return HttpResponse(json.dumps(result), mimetype='text/plain')

class CorpList(object):
    OUR_ALLIANCE = 'Electus Matari'

    def __init__(self, do_all, oldforum, oldkb, oldapi):
        self.corpdict = {}
        self.corporations = []
        self.do_all = do_all
        self.oldforum = oldforum
        self.oldkb = oldkb
        self.oldapi = oldapi
        self.forum_lastseen = mybb_lastseen()

        self.size = 0
        self.forum = 0
        self.forum_p = 0
        self.forum_active = 0
        self.forum_active_p = 0
        self.killboard = 0
        self.killboard_p = 0
        self.killboard_active = 0
        self.killboard_active_p = 0
        self.api_active = 0
        self.api_active_p = 0

    def __iter__(self):
        for corp in self.corporations:
            yield corp

    def add(self, profile):
        if self.do_all or profile.alliance == self.OUR_ALLIANCE:
            if profile.corp not in self.corpdict:
                self.corpdict[profile.corp] = Corporation(profile.corp,
                                                          profile.corpid,
                                                          profile.alliance,
                                                          self.oldforum,
                                                          self.oldkb,
                                                          self.oldapi,
                                                          self.forum_lastseen)
            self.corpdict[profile.corp].add(profile)

    def finalize(self):
        self.corporations = self.corpdict.values()
        self.corporations.sort(lambda a, b: cmp(a.name.lower(), 
                                                b.name.lower()))
        for corp in self.corporations:
            corp.finalize()
            self.size += corp.size
            self.forum += corp.forum
            self.forum_active += corp.forum_active
            self.killboard += corp.killboard
            self.killboard_active += corp.killboard_active
            self.api_active += corp.api_active
        if self.size != 0:
            self.forum_p = int((self.forum / float(self.size)) * 100)
            self.forum_active_p = int((self.forum_active / float(self.size)) * 100)
            self.killboard_p = int((self.killboard / float(self.size)) * 100)
            self.killboard_active_p = int((self.killboard_active /
                                           float(self.size)) * 100)
            self.api_active_p = int((self.api_active /
                                     float(self.size)) * 100)

class Corporation(object):
    def __init__(self, name, corpid, alliance,
                 oldforum, oldkb, oldapi, forum_lastseen):
        self.name = name
        self.alliance = alliance
        self.oldforum = oldforum
        self.oldkb = oldkb
        self.oldapi = oldapi
        self.forum_lastseen = forum_lastseen
        self.kb_lastseen = kb_lastseen(name)
        self.api_lastseen = api_lastseen(name)
        self.members = []
        self.size = corp_size(corpid)
        self.forum = 0
        self.forum_p = 0
        self.forum_active = 0
        self.forum_active_p = 0
        self.killboard = 0
        self.killboard_p = 0
        self.killboard_active = 0
        self.killboard_active_p = 0
        self.api_active = 0
        self.api_active_p = 0

    def add(self, profile):
        assert profile.corp == self.name
        forum = self.forum_lastseen.get(profile.mybb_uid, None)
        kb = self.kb_lastseen.get(profile.name, None)
        api = self.api_lastseen.get(profile.name, None)
        member = Member(profile.name, forum, kb, api,
                        self.oldforum, self.oldkb, self.oldapi)
        if api:
            del self.api_lastseen[profile.name]
        self.members.append(member)

    def finalize(self):
        for name, lastseen in self.api_lastseen.items():
            self.members.append(Member(name,
                                       None,
                                       self.kb_lastseen.get(name, None),
                                       lastseen,
                                       self.oldforum, self.oldkb, self.oldapi))

        for member in self.members:
            if member.forum_lastseen:
                self.forum += 1
            if not member.forum_is_old:
                self.forum_active += 1
            if member.kb_lastseen:
                self.killboard += 1
            if not member.kb_is_old:
                self.killboard_active += 1
            if not member.api_is_old:
                self.api_active += 1

        self.members.sort(lambda a, b: cmp(a.name.lower(), b.name.lower()))

        if self.size == 0:
            return
        self.forum_p = int((self.forum / float(self.size)) * 100)
        self.forum_active_p = int((self.forum_active / float(self.size)) * 100)
        self.killboard_p = int((self.killboard / float(self.size)) * 100)
        self.killboard_active_p = int((self.killboard_active /
                                       float(self.size)) * 100)
        self.api_active_p = int((self.api_active / float(self.size)) * 100)

class Member(object):
    def __init__(self, name, forum, kb, api, oldforum, oldkb, oldapi):
        now = datetime.datetime.utcnow()

        self.name = name

        if forum is not None:
            forum = datetime.datetime.utcfromtimestamp(forum)
        self.forum_lastseen = None
        self.forum_is_old = True
        self.forum_delta = None
        if forum is not None:
            self.forum_lastseen = forum
            self.forum_delta = now - forum
            if self.forum_delta.days <= oldforum:
                self.forum_is_old = False
        self.forumcssclass = "veryold" if self.forum_is_old else ""

        self.kb_lastseen = None
        self.kb_is_old = True
        self.kb_delta = None
        if kb is not None:
            self.kb_lastseen = kb
            self.kb_delta = now - kb
            if self.kb_delta.days <= oldkb:
                self.kb_is_old = False
        self.kbcssclass = "veryold" if self.kb_is_old else ""
        
        self.api_lastseen = None
        self.api_is_old = True
        self.api_delta = None
        if api is not None:
            self.api_lastseen = api
            self.api_delta = now - api
            if self.api_delta.days <= oldapi:
                self.api_is_old = False
        self.apicssclass = "veryold" if self.api_is_old else ""

def corp_size(corpid):
    api = apiroot()
    try:
        result = api.corp.CorporationSheet(corporationID=corpid)
        return result.memberCount
    except:
        return 0

def api_lastseen(corpname):
    try:
        key = APIKey.objects.get(name=corpname, active=True)
    except APIKey.DoesNotExist:
        return {}
    corp = key.corp()
    try:
        cmt = corp.MemberTracking()
    except Exception as e:
        key.message = "Error while accessing /corp/MemberTracking: %s" % str(e)
        key.active = False
        key.save()
        return {}
    return dict((row.name,
                 datetime.datetime.utcfromtimestamp(row.logoffDateTime)
                 if hasattr(row, 'logoffDateTime')
                 else None
                 )
                for row in cmt.members)

def mybb_lastseen():
    db = utils.connect('emforum')
    c = db.cursor()
    c.execute("SELECT uid, lastactive FROM mybb_users")
    return dict(c.fetchall())

def kb_lastseen(corpname):
    db = utils.connect('emkillboard')
    c = db.cursor()
    c.execute("""
SELECT p.plt_name AS name,
       CAST(GREATEST(COALESCE(MAX(invd.ind_timestamp), MAKEDATE(1970, 1)),
                     COALESCE(MAX(k.kll_timestamp), MAKEDATE(1970, 1)))
            AS DATETIME) AS lastseen
FROM kb3_pilots p
     INNER JOIN kb3_corps c ON p.plt_crp_id = c.crp_id
     LEFT JOIN kb3_inv_detail invd ON p.plt_id = invd.ind_plt_id
     LEFT JOIN kb3_kills k ON p.plt_id = k.kll_victim_id
WHERE c.crp_name = %s
GROUP BY p.plt_name
""",
              (corpname,))
    return dict(c.fetchall())

def intval(val):
    try:
        return int(val)
    except:
        return 0
