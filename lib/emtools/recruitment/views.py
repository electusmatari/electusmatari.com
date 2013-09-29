import datetime

from django.contrib import messages
from django.http import Http404
from django.http import HttpResponseRedirect
from django.views.generic.simple import direct_to_template

from emtools.ccpeve.models import apiroot
from emtools.ccpeve.ccpdb import get_typename
from emtools.emauth.decorators import require_mybbgroup

from emtools.recruitment.forms import APIKeyForm
from emtools.recruitment.models import User, Character, Skill, Implant, Standing

PERSONNEL = ['Personnel Manager', 'Council', 'Gradient Personnel Manager']

utc = datetime.datetime.utcfromtimestamp

def view_submit(request):
    if request.method == 'POST':
        form = APIKeyForm(request.POST)
        if form.is_valid():
            user = audit_apikey(request,
                                form.cleaned_data['userid'],
                                form.cleaned_data['apikey'],
                                form.cleaned_data['visibility'])
            if user is None:
                return HttpResponseRedirect('/recruitment/')
            else:
                return direct_to_template(request, 'recruitment/user.html',
                                          extra_context={'audituser': user,
                                                         'tab': 'audits'})
    else:
        form = APIKeyForm()
    return direct_to_template(request, 'recruitment/submit.html',
                              extra_context={'form': form,
                                             'tab': 'submit'})

@require_mybbgroup(PERSONNEL)
def view_audits(request):
    userlist = User.objects.filter(visibility=request.user.profile.corp)
    return direct_to_template(request, 'recruitment/audits.html',
                              extra_context={'tab': 'audits',
                                             'userlist': userlist})

@require_mybbgroup(PERSONNEL)
def view_single_audit(request, userid):
    try:
        user = User.objects.get(visibility=request.user.profile.corp,
                                id=userid)
    except User.DoesNotExist:
        raise Http404
    return direct_to_template(request, 'recruitment/user.html',
                              extra_context={'audituser': user,
                                             'tab': 'audits'})

def audit_apikey(request, userid, apikey, visibility):
    try:
        api = apiroot().auth(keyID=userid, vCode=apikey)
        characters = api.account.Characters()
    except Exception as e:
        messages.add_message(request, messages.ERROR,
                             "Error during API call: %s" % (str(e),))
        return None

    user = User(userid=userid,
                visibility=visibility)
    user.save()
    for row in characters.characters:
        try:
            charapi = api.character(row.characterID)
            sheet = charapi.CharacterSheet()
            standings = charapi.Standings()
            info = api.eve.CharacterInfo(characterID=row.characterID)
        except Exception as e:
            messages.add_message(request, messages.ERROR,
                                 "Error during API call: %s" % (str(e),))
            return None
        char = Character(user=user,
                         characterid=row.characterID,
                         name=row.name,
                         gender=sheet.gender,
                         race=sheet.race,
                         bloodline=sheet.bloodLine,
                         security=info.securityStatus,
                         graduation=utc(sheet.DoB),
                         skillpoints=sum(skill.skillpoints for skill
                                          in sheet.skills),
                         wallet=sheet.balance,
                         corpid=sheet.corporationID,
                         corpname=sheet.corporationName,
                         corpjoin=utc(info.corporationDate))
        if hasattr(sheet, 'allianceID') and sheet.allianceID > 0:
            char.allianceid = sheet.allianceID
            char.alliancename = sheet.allianceName
            if hasattr(info, 'allianceDate'):
                char.alliancejoin = utc(info.allianceDate)
        char.save()
        for skill in sheet.skills:
            typename = get_typename(skill.typeID)
            if typename is None:
                typename = "<TypeID %s>" % skill.typeID
            Skill.objects.create(character=char,
                                 typeid=skill.typeID,
                                 typename=typename,
                                 skillpoints=skill.skillpoints,
                                 level=skill.level,
                                 published=skill.published)
        for bonus in ['charismaBonus', 'intelligenceBonus', 'memoryBonus',
                      'perceptionBonus', 'willpowerBonus']:
            if not hasattr(sheet.attributeEnhancers, bonus):
                continue
            name = bonus[:-5].title()
            obj = getattr(sheet.attributeEnhancers, bonus)
            Implant.objects.create(character=char,
                                   attribute=name,
                                   augmentor=obj.augmentatorName,
                                   value=obj.augmentatorValue)
        for faction in standings.characterNPCStandings.factions:
            Standing.objects.create(character=char,
                                    entitytype="faction",
                                    fromid=faction.fromID,
                                    fromname=faction.fromName,
                                    standing=faction.standing)
        for corp in standings.characterNPCStandings.NPCCorporations:
            Standing.objects.create(character=char,
                                    entitytype="corp",
                                    fromid=corp.fromID,
                                    fromname=corp.fromName,
                                    standing=corp.standing)
        for agent in standings.characterNPCStandings.agents:
            Standing.objects.create(character=char,
                                    entitytype="agent",
                                    fromid=agent.fromID,
                                    fromname=agent.fromName,
                                    standing=agent.standing)
    return user
