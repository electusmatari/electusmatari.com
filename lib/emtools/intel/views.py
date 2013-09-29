import json
import logging

from django.contrib import messages
from django.db import connection
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.views.generic.list_detail import object_list
from django.views.generic.simple import direct_to_template

from emtools.ccpeve import eveapi
from emtools.ccpeve.models import apiroot, APIKey
from emtools.ccpeve import ccpdb
from emtools.emauth.decorators import require_mybbgroup, require_account
from emtools.intel.models import Alliance, Corporation, Pilot, Trace
from emtools.intel.models import ChangeLog, TrackedEntity
from emtools.intel.forms import TraceForm
import emtools.ccpeve.igb as igb

@require_mybbgroup('Electus Matari')
def view_overview(request):
    return object_list(request, ChangeLog.objects.all(),
                       paginate_by=20,
                       template_name='intel/overview.html',
                       extra_context={'tab': 'overview'},
                       template_object_name='changelog')

@require_mybbgroup('Electus Matari')
def view_locators(request):
    try:
        jumps = int(request.GET.get('jumps', '3'))
    except ValueError:
        jumps = 3
    system = request.GET.get('system', '')
    if system == '':
        system = request.META.get('HTTP_EVE_SOLARSYSTEMNAME', '')
    agents = ccpdb.get_locator_agents(system, jumps)
    for agent in agents:
        agent['stationinfo'] = igb.ShowInfoStation(agent['stationid'])
    return direct_to_template(request, 'intel/locators.html',
                              extra_context={'tab': 'locators',
                                             'system': system,
                                             'agent_list': agents,
                                             'trust': igb.RequestTrust('http://www.electusmatari.com/')})

@require_mybbgroup('Electus Matari')
def view_submitpilots(request):
    if request.method == 'POST':
        names = request.POST.get("names", "")
        if "I found" in names and "for you" in names:
            messages.add_message(request, messages.ERROR,
                                 'You are trying to submit a locator trace. '
                                 'Please do that under "Submit Trace", use '
                                 'this form to submit pilot names.')
            return HttpResponseRedirect('/intel/submit/pilots/')
        names = [name.strip() for name in names.split("\n") if name != '']
        api = apiroot()
        charids = api.eve.CharacterID(names=",".join(names))
        charname2id = dict([(char.name, char.characterID)
                            for char in charids.characters])
        for name in names:
            if name in charname2id and charname2id[name] == 0:
                messages.add_message(request, messages.ERROR,
                                     "Pilot %s not found" % name)
                continue
            try:
                get_pilot(name, charname2id[name])
            except:
                messages.add_message(request, messages.ERROR,
                                     "Pilot %s not found" % name)
                continue
            messages.add_message(request, messages.INFO,
                                 "Pilot %s added" % name)
        return HttpResponseRedirect('/intel/submit/pilots/')
    return direct_to_template(request, 'intel/submitpilots.html',
                              extra_context={'tab': 'submitpilots'})

@require_mybbgroup('Electus Matari')
def view_tracking(request):
    if request.method == 'POST':
        action = request.POST.get('action', 'None')
        log = logging.getLogger('intel')
        if action == 'remove':
            pk = request.POST.get('id', None)
            if pk is not None:
                try:
                    obj = TrackedEntity.objects.get(pk=pk)
                except TrackedEntity.DoesNotExist:
                    messages.add_message(request, messages.ERROR,
                                         "This tracking does not exist")
                    return HttpResponseRedirect('/intel/tracking/')
                name = unicode(obj)
                obj.delete()
                messages.add_message(request, messages.INFO,
                                     "Removed tracking of %s" % name)
                log.info("User %s removed tracking of %s" %
                         (request.user.profile.mybb_username, name))
            return HttpResponseRedirect('/intel/tracking/')
        elif action == 'add':
            name = request.POST.get('name', None)
            if name is not None:
                name = name.strip()
            try:
                corp = get_corp(name)
                obj, created = TrackedEntity.objects.get_or_create(
                    corporation=corp
                    )
                if created:
                    messages.add_message(request, messages.INFO,
                                         "Now tracking corp %s" % corp.name)
                    log.info("User %s added tracking of %s" %
                             (request.user.profile.mybb_username, corp.name))
                else:
                    messages.add_message(request, messages.ERROR,
                                         "Already tracking corp %s" %
                                         corp.name)
                return HttpResponseRedirect('/intel/tracking/')
            except:
                pass
            try:
                alliance = get_alliance(name)
                obj, created = TrackedEntity.objects.get_or_create(
                    alliance=alliance
                    )
                if created:
                    messages.add_message(request, messages.INFO,
                                         "Now tracking alliance %s" % alliance.name)
                    log.info("User %s added tracking of %s" %
                             (request.user.profile.mybb_username, alliance.name))
                else:
                    messages.add_message(request, messages.ERROR,
                                         "Already tracking alliance %s" %
                                         alliance.name)
                return HttpResponseRedirect('/intel/tracking/')
            except:
                pass
            messages.add_message(request, messages.ERROR,
                                 "Unknown entity %s" % name)
            return HttpResponseRedirect('/intel/tracking/')
    queryset = TrackedEntity.objects.all()
    return direct_to_template(request, 'intel/tracking.html',
                              extra_context={'tab': 'tracking',
                                             'track_list': queryset})

@require_mybbgroup('Electus Matari')
def view_search(request):
    query = request.GET.get('q', '')
    try:
        corp = Corporation.objects.get(name=query)
        return HttpResponseRedirect('/intel/corp/%s' % corp.name)
    except Corporation.DoesNotExist:
        pass
    try:
        ally = Alliance.objects.get(name=query)
        return HttpResponseRedirect('/intel/alliance/%s' % ally.name)
    except Alliance.DoesNotExist:
        pass
    try:
        pilot = Pilot.objects.get(name=query)
        return HttpResponseRedirect('/intel/pilot/%s' % pilot.name)
    except Pilot.DoesNotExist:
        pass
    corps = Corporation.objects.filter(Q(name__icontains=query) |
                                       Q(ticker__icontains=query))[0:50]
    alliances = Alliance.objects.filter(Q(name__icontains=query) |
                                        Q(ticker__icontains=query))[0:50]
    pilots = Pilot.objects.filter(name__icontains=query)[0:50]
    return direct_to_template(request, 'intel/search.html',
                              extra_context={'tab': 'overview',
                                             'corp_list': corps,
                                             'alliance_list': alliances,
                                             'pilot_list': pilots})

@require_mybbgroup('Electus Matari')
def view_searchajax(request):
    term = request.GET.get("term", "")
    result = []
    for corp in Corporation.objects.filter(Q(name__icontains=term) |
                                           Q(ticker__icontains=term)):
        result.append({'label': corp.fullname(),
                       'value': corp.name,
                       'type': 'corp'})
    for ally in Alliance.objects.filter(Q(name__icontains=term) |
                                        Q(ticker__icontains=term)):
        result.append({'label': ally.fullname(),
                       'value': ally.name,
                       'type': 'alliance'})
    for pilot in Pilot.objects.filter(name__icontains=term):
        result.append({'label': pilot.name,
                       'value': pilot.name,
                       'type': 'pilot'})
    result.sort(lambda a, b: cmp(a['label'].lower(), b['label'].lower()))
    return HttpResponse(json.dumps(result), mimetype='text/plain')


@require_mybbgroup('Electus Matari')
def view_searchajaxsystems(request):
    term = request.GET.get("term", "")
    c = connection.cursor()
    c.execute("SELECT s.solarsystemname, s.security, r.regionname "
              "FROM ccp.mapsolarsystems s "
              "     INNER JOIN ccp.mapregions r "
              "       ON s.regionid = r.regionid "
              "WHERE s.solarsystemname ILIKE %s "
              "ORDER BY s.solarsystemname ASC",
              ("%s%%" % term,))
    result = []
    for name, security, region in c.fetchall():
        result.append({'label': "%s, %s (%.1f)" % (name, region, security),
                       'value': name})
    return HttpResponse(json.dumps(result), mimetype='text/plain')

@require_mybbgroup('Electus Matari')
def view_pilot(request, name):
    try:
        pilot = Pilot.objects.get(name=name)
    except Pilot.DoesNotExist:
        raise Http404
    return object_list(request, Trace.objects.filter(pilot__name=name),
                       paginate_by=23,
                       template_name='intel/pilot.html',
                       extra_context={'tab': 'overview',
                                      'pilot': pilot},
                       template_object_name='trace')

@require_mybbgroup('Electus Matari')
def view_corp(request, name):
    try:
        corp = Corporation.objects.get(name=name)
    except Corporation.DoesNotExist:
        raise Http404
    # FIXME: Top 10 systems
    return object_list(request,
                       ChangeLog.objects.filter(
            (Q(oldcorp=corp) & ~Q(newcorp=corp)) |
            (Q(newcorp=corp) & ~Q(oldcorp=corp))
            ),
                       paginate_by=23,
                       template_name='intel/corp.html',
                       extra_context={'tab': 'overview',
                                      'corp': corp,
                                      'tracked': corp.trackedentity_set.count() > 0},
                       template_object_name='changelog')

@require_mybbgroup('Electus Matari')
def view_alliance(request, name):
    try:
        alliance = Alliance.objects.get(name=name)
    except Alliance.DoesNotExist:
        raise Http404
    # FIXME! Top 10 systems
    return object_list(request,
                       ChangeLog.objects.filter(
            (Q(oldalliance=alliance) & ~Q(newalliance=alliance)) |
            (Q(newalliance=alliance) & ~Q(oldalliance=alliance))
            ),
                       paginate_by=23,
                       template_name='intel/alliance.html',
                       extra_context={'tab': 'overview',
                                      'alliance': alliance,
                                      'tracked': alliance.trackedentity_set.count() > 0},
                       template_object_name='changelog')

@require_account
def view_submit(request):
    if request.method == 'POST':
        form = TraceForm(request.POST)
        if form.is_valid():
            try:
                pilot = get_pilot(form.cleaned_data['target'])
            except:
                messages.add_message(request, messages.ERROR,
                                     "Unknown pilot %s" % 
                                     form.cleaned_data['target'])
                return HttpResponseRedirect('/intel/submit/')
            trace, created = Trace.objects.get_or_create(
                timestamp=form.cleaned_data['timestamp'],
                pilot=pilot,
                corporation=pilot.corporation,
                alliance=pilot.corporation.alliance,
                system=form.cleaned_data['system'],
                systemid=ccpdb.get_systemid(form.cleaned_data['system']),
                station=form.cleaned_data['station'],
                stationid=ccpdb.get_stationid(form.cleaned_data['station']),
                agent=form.cleaned_data['agent'],
                online=form.cleaned_data['online'],
                defaults={'submitter': request.user})
            if created:
                messages.add_message(request, messages.INFO,
                                     "Trace submitted")
            else:
                messages.add_message(request, messages.ERROR,
                                     "Trace already known")
            return HttpResponseRedirect('/intel/submit/')
    else:
        form = TraceForm()
    return object_list(request, Trace.objects.all(),
                       paginate_by=5,
                       template_name='intel/submit.html',
                       extra_context={'tab': 'submit',
                                      'form': form},
                       template_object_name='trace')

def get_pilot(name=None, charid=None):
    api = apiroot()
    try:
        if charid is None:
            charid = api.eve.CharacterID(names=name).characters[0].characterID
        charinfo = api.eve.CharacterInfo(characterID=charid)
    except Exception as e:
        raise UnknownPilotError("Unknown pilot %s (%s): %s" %
                                (name, charid, str(e)))
    if hasattr(charinfo, 'allianceID'):
        alliance = get_alliance(charinfo.alliance, charinfo.allianceID)
    else:
        alliance = None

    corp = get_corp(charinfo.corporation, charinfo.corporationID)

    pilot, created = Pilot.objects.get_or_create(
        name=charinfo.characterName,
        characterid=charinfo.characterID,
        defaults={'corporation': corp,
                  'alliance': alliance,
                  'security': charinfo.securityStatus})
    if created:
        ChangeLog.objects.create(pilot=pilot,
                                 oldcorp=None,
                                 oldalliance=None,
                                 newcorp=corp,
                                 newalliance=alliance)
    else:
        if pilot.corporation != corp or pilot.alliance != alliance:
            ChangeLog.objects.create(pilot=pilot,
                                     oldcorp=pilot.corporation,
                                     oldalliance=pilot.alliance,
                                     newcorp=corp,
                                     newalliance=alliance)
        pilot.corporation = corp
        pilot.alliance = alliance
        pilot.security = charinfo.securityStatus
        pilot.save()
    return pilot

def get_alliance(name=None, allianceid=None):
    api = apiroot()
    try:
        if name is None:
            name = api.eve.CharacterName(ids=allianceid).characters[0].name
        if allianceid is None:
            allianceid = api.eve.CharacterID(names=name).characters[0].characterID
        alliance_list = api.eve.AllianceList().alliances
    except Exception as e:
        raise UnknownAllianceError("Error getting alliance list for alliance "
                                   "%s (%s): %s" %
                                   (name, allianceid, str(e)))
    found = False
    for alliance in alliance_list:
        if allianceid is not None and alliance.allianceID == allianceid:
            if name is None:
                name = alliance.name
            found = True
        if name is not None and alliance.name == name:
            if allianceid is None:
                allianceid = alliance.allianceID
            found = True
    if not found:
        raise UnknownAllianceError('Alliance %s (%s) not found in API' %
                                   (name, allianceid))
    alliance, created = Alliance.objects.get_or_create(
        allianceid=allianceid,
        defaults={'name': name})
    if not created:
        alliance.name = name
        alliance.save()
    return alliance

def get_corp(name=None, corpid=None):
    api = apiroot()
    try:
        if corpid is None:
            corpid = api.eve.CharacterID(names=name).characters[0].characterID
        corpsheet = api.corp.CorporationSheet(corporationID=corpid)
        if name is None:
            name = corpsheet.corporationName
    except Exception as e:
        raise UnknownCorporationError("Unknown corporation %s (%s): %s" %
                                      (name, corpid, str(e)))
    if hasattr(corpsheet, 'allianceName'):
        alliance = get_alliance(corpsheet.allianceName,
                                corpsheet.allianceID)
    else:
        alliance = None
    corp, created = Corporation.objects.get_or_create(
        corporationid=corpid,
        defaults={'name': name,
                  'alliance': alliance,
                  'ticker': corpsheet.ticker,
                  'members': corpsheet.memberCount})
    if not created:
        # Corp existed. If the alliance changed, all pilots change.
        if corp.alliance != alliance:
            for pilot in corp.pilot_set.all():
                ChangeLog.objects.create(pilot=pilot,
                                         oldcorp=corp,
                                         oldalliance=corp.alliance,
                                         newcorp=corp,
                                         newalliance=alliance)
                pilot.alliance = alliance
                pilot.save()
        # Update in any case to change the timestamp
        corp.name = name
        corp.alliance = alliance
        corp.ticker = corpsheet.ticker
        corp.members = corpsheet.memberCount
        corp.save()
    return corp

class UnknownEntityError(Exception):
    pass

class UnknownPilotError(UnknownEntityError):
    pass

class UnknownCorporationError(UnknownEntityError):
    pass

class UnknownAllianceError(UnknownEntityError):
    pass

def update_all():
    """
    Update all intel information.
    """
    api = apiroot()
    apicorp = APIKey.objects.get(name="Gradient").corp()
    alliances = set()
    # Alliance list
    for alliance in api.eve.AllianceList().alliances:
        alliances.add(alliance.allianceID)
        ally = get_alliance(alliance.name, alliance.allianceID)
        ally.ticker = alliance.shortName
        ally.members = alliance.memberCount
        ally.save()
        if ally.trackedentity_set.count() != 0:
            for corp in alliance.memberCorporations:
                get_corp(corpid=corp.corporationID)
    # Alliance standings
    # Bugged: contact.contactID can be dead alliance
    # for contact in apicorp.ContactList().allianceContactList:
    #     try:
    #         if contact.contactID in alliances:
    #             entity = get_alliance(allianceid=contact.contactID)
    #         else:
    #             entity = get_corp(corpid=contact.contactID)
    #     except UnknownEntityError:
    #         continue
    #     entity.standing = contact.standing
    #     entity.save()
    # Tracked entities
    for tracked in TrackedEntity.objects.all():
        if tracked.corporation:
            get_corp(tracked.corporation.name,
                     tracked.corporation.corporationid)
        if tracked.alliance:
            get_alliance(tracked.alliance.name,
                         tracked.alliance.allianceid)
    # Tracked pilots
    for pilot in Pilot.objects.all():
        if (pilot.corporation.trackedentity_set.count() > 0 or
            (pilot.alliance is not None and pilot.alliance.trackedentity_set.count() > 0)):
            get_pilot(pilot.name, pilot.characterid)
