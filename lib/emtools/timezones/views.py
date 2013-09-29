import datetime
import dateutil.tz as tz
import dateutil.parser as parser

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.views.generic.simple import direct_to_template

from emtools.emauth.decorators import require_mybbgroup
from emtools.timezones.models import TZConfig
from emtools.timezones.forms import TZConfigForm

TZDEFAULTS = [
    ('EVT', 'UTC'),
    ('Europe', 'Europe/Berlin'),
    ('US', 'US/Eastern'),
    ('NZ', 'NZ')
]

@require_mybbgroup('Electus Matari')
def view_time(request):
    try:
        offset = int(request.GET.get("offset", 0))
    except ValueError:
        offset = 0
    groups = get_groups(request, get_time(request.GET.get("time", ""),
                                          offset))
    return direct_to_template(request, 'timezones/time.html',
                              extra_context={'tab': 'time',
                                             'group_list': groups})

def get_time(timestring, offset):
    utc = tz.tzutc()
    default = datetime.datetime.utcnow().replace(tzinfo=utc)
    try:
        parsed = parser.parse(timestring, default=default, fuzzy=True)
        parsedtz = parsed.replace(tzinfo=tz.tzoffset(None, offset * 60 * 60))
        return parsedtz.astimezone(utc)
    except ValueError:
        return default

def get_groups(request, utcnow):
    offsets = {}

    for (name, tzname) in TZDEFAULTS:
        usertz = tz.gettz(tzname)
        usernow = utcnow.astimezone(usertz)
        offset_delta = usernow.utcoffset()
        offset = offset_delta.days * 24 + offset_delta.seconds / 3600
        offsets[offset] = TZGroup(usernow, offset, name=name)

    for conf in TZConfig.objects.filter(Q(public=True) |
                                        Q(user=request.user)):
        usertz = tz.gettz(conf.timezone)
        usernow = utcnow.astimezone(usertz)
        offset_delta = usernow.utcoffset()
        offset = offset_delta.days * 24 + offset_delta.seconds / 3600
        if offset not in offsets:
            tzgroup = TZGroup(usernow, offset)
            offsets[offset] = tzgroup
        else:
            tzgroup = offsets[offset]
        if request.user == conf.user:
            tzgroup.setcurrent()
        tzgroup.adduser(conf.user)

    result = offsets.items()
    result.sort()
    return [x[1] for x in result]

class TZGroup(object):
    def __init__(self, now, offset, name=None):
        self.name = name
        self.now = now
        self.offset = offset
        self.users = []
        self.current = False

    def niceoffset(self):
        return "%+03i" % self.offset

    def adduser(self, user):
        self.users.append(user)
        self.users.sort(lambda a, b: cmp(a.profile.mybb_username.lower(),
                                         b.profile.mybb_username.lower()))

    def setcurrent(self, value=True):
        self.current = value

    def cssclass(self):
        if self.current:
            return "tzcurrent"
        elif self.offset == 0:
            return "evt"
        else:
            return ""

@require_mybbgroup('Electus Matari')
def view_config(request):
    try:
        tzconfig = TZConfig.objects.get(user=request.user)
    except TZConfig.DoesNotExist:
        tzconfig = None

    if request.method == 'POST':
        if request.POST.get('action', '') == 'delete':
            if tzconfig is not None:
                tzconfig.delete()
                messages.add_message(request, messages.INFO,
                                     "Time zone configuration deleted.")
            return HttpResponseRedirect('/tools/timezones/')
        if tzconfig is not None:
            form = TZConfigForm(request.POST, instance=tzconfig)
        else:
            form = TZConfigForm(request.POST)
        if form.is_valid():
            tzconfig = form.save(commit=False)
            tzconfig.user = request.user
            tzconfig.save()
            messages.add_message(request, messages.INFO,
                                 "Time zone configuration saved.")
            return HttpResponseRedirect('/tools/timezones/')
    else:
        if tzconfig is not None:
            form = TZConfigForm(instance=tzconfig)
        else:
            form = TZConfigForm()

    return direct_to_template(request, 'timezones/config.html',
                              extra_context={'tab': 'config',
                                             'form': form})
    
