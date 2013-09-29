import datetime

from django.db import connection
from django.views.generic.list_detail import object_list
from django.views.generic.simple import direct_to_template
from emtools.ccpeve.models import apiroot
import emtools.ccpeve.igb as igb

import sys
sys.path.append("/home/forcer/Projects/evecode/web/gradient.electusmatari.com/data/python/")

from gradient.uploader.models import FacWarSystem
from emtools.intel.models import Pilot, Corporation, Change

from emtools.emauth.decorators import require_mybbgroup

@require_mybbgroup(['Electus Matari', 'Ally', 'Militia Intel'])
def view_map(request):
    lu = FacWarSystem.objects.all()[0].cachetimestamp
    minmatar = FacWarSystem.objects.filter(
        occupyingfactionname='Minmatar Republic',
        victorypoints__gt=0).order_by('-victorypoints')
    amarr = FacWarSystem.objects.filter(
        occupyingfactionname='Amarr Empire',
        victorypoints__gt=0).order_by('-victorypoints')
    gallente = FacWarSystem.objects.filter(
        occupyingfactionname='Gallente Federation',
        victorypoints__gt=0).order_by('-victorypoints')
    caldari = FacWarSystem.objects.filter(
        occupyingfactionname='Caldari State',
        victorypoints__gt=0).order_by('-victorypoints')
    return direct_to_template(request, 'fw/map.html',
                              extra_context={
            'tab': 'map',
            'lastupdated': lu,
            'map': [('Minmatar Republic', '/media/img/icons/minmatar.png',
                     minmatar),
                    ('Amarr Empire', '/media/img/icons/amarr.png', amarr),
                    ('Gallente Federation', '/media/img/icons/gallente.png',
                     gallente),
                    ('Caldari State', '/media/img/icons/caldari.png',
                     caldari),
                    ]
            })

def corp_image(corpid):
    try:
        corp = Corporation.objects.select_related(
            depth=1).get(corporationid=corpid)
    except Corporation.DoesNotExist:
        return None
    return faction_image(corp.faction)

def pilot_image_and_corp(charid):
    try:
        pilot = Pilot.objects.select_related(
            depth=2).get(characterid=charid)
    except Pilot.DoesNotExist:
        return None, None
    if pilot.corporation is None:
        return None, None
    return (faction_image(pilot.corporation.faction),
            pilot.corporation)

def faction_image(faction):
    if faction is None:
        return None
    return factionname_image(faction.name)

def factionname_image(factionname):
    if factionname == 'Minmatar Republic':
        return '/media/img/icons/minmatar16.png'
    elif factionname == 'Amarr Empire':
        return '/media/img/icons/amarr16.png'
    elif factionname == 'Gallente Federation':
        return '/media/img/icons/gallente16.png'
    elif factionname == 'Caldari State':
        return '/media/img/icons/caldari16.png'
    else:
        return None

@require_mybbgroup(['Electus Matari', 'Ally', 'Militia Intel'])
def view_topstats(request):
    api = apiroot()
    fwts = api.eve.FacWarTopStats()

    vplastweek = Bag(characters=[],
                     corporations=[],
                     factions=[])
    for rank, entry in enumerate(fwts.characters.VictoryPointsLastWeek):
        image, corp = pilot_image_and_corp(entry.characterID)
        vplastweek.characters.append(Bag(rank=rank + 1,
                                         id=entry.characterID,
                                         name=entry.characterName,
                                         points=entry.victoryPoints,
                                         igb=igb.ShowInfoCharacter(entry.characterID),
                                         faction=image,
                                         corp="(Unknown)" if corp is None else corp.name,
                                         corpigb="" if corp is None else igb.ShowInfoCorp(corp.corporationid)))
    for rank, entry in enumerate(fwts.corporations.VictoryPointsLastWeek):
        vplastweek.corporations.append(Bag(rank=rank + 1,
                                           id=entry.corporationID,
                                           name=entry.corporationName,
                                           points=entry.victoryPoints,
                                           igb=igb.ShowInfoCorp(entry.corporationID),
                                           faction=corp_image(entry.corporationID)))
    for rank, entry in enumerate(fwts.factions.VictoryPointsLastWeek):
        vplastweek.factions.append(Bag(rank=rank + 1,
                                       id=entry.factionID,
                                       name=entry.factionName,
                                       points=entry.victoryPoints,
                                       igb="",
                                       faction=factionname_image(entry.factionName)))
    return direct_to_template(request, 'fw/topstats.html',
                              extra_context={'tab': 'topstats',
                                             'vplastweek': vplastweek,
                                             'cacheduntil': datetime.datetime.utcfromtimestamp(fwts._meta.cachedUntil)})

class Bag(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

@require_mybbgroup(['Electus Matari', 'Ally', 'Militia Intel'])
def view_corps(request):
    corp_lists = {}
    known_members = {}
    amarr_standings = 0
    qs = Corporation.objects.exclude(
        faction=None
        ).exclude(
        members=0
        ).order_by("-members", "name")
    for corp in qs:
        corp_lists.setdefault(corp.faction.name, [])
        corp_lists[corp.faction.name].append(corp)
        known_members.setdefault(corp.faction.name, 0)
        if corp.members is not None:
            known_members[corp.faction.name] += corp.members
        if (corp.faction.name == 'Amarr Empire' and
            corp.standing is not None and corp.standing == -10):
            amarr_standings += corp.members
    api = apiroot()
    fws = api.eve.FacWarStats()
    all_members = dict((row.factionName, row.pilots)
                       for row in fws.factions)
    return direct_to_template(request, 'fw/corps.html',
                              extra_context={
            'tab': 'corps',
            'amarr_standings': amarr_standings,
            'amarr_percentage': 100 * (amarr_standings /
                                       float(all_members['Amarr Empire'])),
            'corp_lists': [(name, corp_lists[name], image,
                            known_members[name], all_members[name],
                            100 * (known_members[name] /
                                   float(all_members[name])),
                            )
                           for (name, image) in
                           [('Amarr Empire', '/media/img/icons/amarr.png'),
                            ('Minmatar Republic', '/media/img/icons/minmatar.png'),
                            ('Caldari State', '/media/img/icons/caldari.png'),
                            ('Gallente Federation', '/media/img/icons/gallente.png')]
                           ]})

@require_mybbgroup(['Electus Matari', 'Ally', 'Militia Intel'])
def view_corpchanges(request):
    qs = Change.objects.filter(changetype='faction').order_by("-timestamp")
    qs = qs.select_related(depth=1)
    return object_list(request, qs,
                       paginate_by=100,
                       template_name='fw/corpchanges.html',
                       extra_context={'tab': 'corpchanges'},
                       template_object_name='change')


# The following was written before I realized I have an
# intel.models.Change model ...

#     c = connection.cursor()
#     c.execute("SELECT (SELECT COUNT(*) FROM uploader_corpfactionhistory "
#               "        WHERE factionid != 0) "
#               "       + "
#               "       (SELECT COUNT(*) FROM uploader_corpfactionhistory "
#               "        WHERE endtimestamp IS NOT NULL "
#               "        AND factionid != 0)")
#     count = c.fetchone()[0]
#     try:
#         pagenum = int(request.GET.get('page', 1))
#     except ValueError:
#         pagenum = 1
#     last_page = (count / 100) + 1
#     if pagenum > last_page:
#         pagenum = last_page
# 
#     qs = Corporation.objects.raw("""
# SELECT c.*,
#        f.id AS faction_id, -- overwrite the above
#        sq.action AS changeaction,
#        sq.timestamp AS changetimestamp,
#        sq.factionid AS changefactionid
# FROM ((SELECT corporationid,
#               'joined' AS action,
#               factionid,
#               starttimestamp AS timestamp
#        FROM uploader_corpfactionhistory
#        WHERE factionid != 0)
#       UNION
#       (SELECT corporationid,
#               'left' AS action,
#               factionid,
#               endtimestamp AS timestamp
#        FROM uploader_corpfactionhistory
#        WHERE endtimestamp IS NOT NULL
#          AND factionid != 0)) AS sq
#      INNER JOIN intel_corporation c ON sq.corporationid = c.corporationid
#      INNER JOIN intel_faction f ON sq.factionid = f.factionid
# ORDER BY sq.timestamp DESC
# LIMIT 100 OFFSET %s
# """, [(pagenum - 1) * 100])
#     p = Paginator(qs, 100)
#     # Hacky
#     p._count = count
#     page_obj = p.page(pagenum)
#     return direct_to_template(request, 'fw/corpchanges.html',
#                               extra_context={'tab': 'corpchanges',
#                                              'change_list': qs,
#                                              'is_paginated': last_page > 1,
#                                              'page_obj': page_obj,
#                                              'paginator': p})

    # Doesn't work because raw query sets do not support the count()
    # method
    #
    # return object_list(request, qs,
    #                    paginate_by=100,
    #                    template_name='fw/corpchanges.html',
    #                    extra_context={'tab': 'corpchanges'},
    #                    template_object_name='change')
