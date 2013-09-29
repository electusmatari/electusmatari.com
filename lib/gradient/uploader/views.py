import datetime
import json
import os
import random

from django.core.mail import mail_admins
from django.db.models import Max
from django.db import connection
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.servers.basehttp import FileWrapper
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.simple import direct_to_template

from gradient import dbutils

from gradient.uploader.models import AuthToken, Upload
from gradient.uploader.models import CorpFactionHistory
from gradient.uploader.models import FacWarSystem, FacWarSystemHistory
from gradient.uploader.models import MarketHistory, MarketHistoryLastUpload
from gradient.uploader.models import MarketOrder, MarketOrderLastUpload

from emtools.intel.models import Pilot, Corporation, Faction

def view_overview(request):
    if request.user.is_authenticated():
        try:
            token = AuthToken.objects.get(user=request.user).tokenstring
        except AuthToken.DoesNotExist:
            token = None
    else:
        token = None
    isigb = 'EVE-IGB' in request.META.get('HTTP_USER_AGENT', '')
    return direct_to_template(
        request, 'uploader/overview.html',
        extra_context={'auth_token': token,
                       'isigb': isigb})

def view_token(request):
    if request.user.is_authenticated():
        try:
            token = AuthToken.objects.get(user=request.user)
        except AuthToken.DoesNotExist:
            token = None
    else:
        token = None
    if request.method == 'POST':
        if token is not None:
            token.tokenstring = generate_auth_token()
            token.save()
        elif request.user.is_authenticated():
            AuthToken.objects.create(
                user=request.user,
                tokenstring=generate_auth_token()
                )
        return HttpResponseRedirect('/uploader/token/')
    return direct_to_template(
        request, 'uploader/token.html',
        extra_context={'auth_token': "" if token is None
                       else token.tokenstring})

TOKENS = 'abcdefghijklmnopqristuvwxyz'
TOKENS += TOKENS.upper()
TOKENS += "0123456789"

def generate_auth_token():
    return "".join(TOKENS[random.randint(0, len(TOKENS) - 1)]
                   for i in range(64))


FILESDIR = "/srv/emcom/electusmatari.com/web/gradient.electusmatari.com/uploader/files/"

def view_files(request, filename):
    if filename == 'gdu.exe':
        fullname = os.path.join(FILESDIR, filename)
        try:
            fileobj = open(fullname)
        except:
            raise Http404
        response = HttpResponse(FileWrapper(fileobj),
                                content_type="application/octet-stream")
        response['Content-Disposition'] = 'attachment; filename=gdu.exe'
        return response
    elif filename == 'version.txt':
        fullname = os.path.join(FILESDIR, filename)
        try:
            fileobj = open(fullname)
        except:
            raise Http404
        return HttpResponse(fileobj.read(),
                            content_type="text/plain")
    else:
        raise Http404

def view_auto(request):
    isigb = 'EVE-IGB' in request.META.get('HTTP_USER_AGENT', '')
    regionname = request.META.get('HTTP_EVE_REGIONNAME', None)
    regionid = dbutils.get_itemid(regionname)
    return direct_to_template(
        request, 'uploader/auto.html',
        extra_context={'isigb': isigb,
                       'regionid': regionid,
                       'regionname': regionname,
                       })

@csrf_exempt
def json_suggest_markethistory(request):
    regionname = request.META.get('HTTP_EVE_REGIONNAME', None)
    if regionname is None:
        return HttpResponse(json.dumps([]), content_type="text/json")
    regionid = dbutils.get_itemid(regionname)
    result = []
    c = connection.cursor()
    c.execute("""
SELECT t.typeid,
       (SELECT MAX(h.cachetimestamp AT TIME ZONE 'UTC')
        FROM uploader_markethistorylastupload h
        WHERE regionid = %s
          AND h.typeid = t.typeid) AS timestamp
FROM index_index t
WHERE NOT t.refineable
ORDER BY timestamp ASC, t.typeid ASC
""", (regionid,))
    midnight = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0,
                                                  microsecond=0)
    result = [typeid for (typeid, timestamp) in c.fetchall()
              if timestamp is None or timestamp < midnight]
    return HttpResponse(json.dumps(result), content_type="text/json")

@csrf_exempt
def json_suggest_marketorders(request):
    regionname = request.META.get('HTTP_EVE_REGIONNAME', None)
    if regionname is None:
        return HttpResponse(json.dumps([]), content_type="text/json")
    regionid = dbutils.get_itemid(regionname)
    c = connection.cursor()
    c.execute("""
SELECT typeid,
       (SELECT MIN(DATE_PART('days', (NOW() at time zone 'UTC')
                                      - h.cachetimestamp)) AS age
        FROM uploader_marketorderlastupload h
        WHERE regionid = %s
          AND h.typeid = mo.typeid) AS age
FROM industry_marketorder mo
     INNER JOIN ccp.stastations st
       ON mo.stationid = st.stationid
     INNER JOIN ccp.mapsolarsystems sys
       ON st.solarsystemid = sys.solarsystemid
WHERE sys.regionid = %s
ORDER BY age DESC, typeid ASC
""",
              (regionid, regionid))
    have = set(typeid for (typeid, age) in c.fetchall()
               if age is None or age > 0)
    c.execute("""
SELECT typeid,
       (SELECT MIN(DATE_PART('days', (NOW() at time zone 'UTC')
                                      - h.cachetimestamp)) AS age
        FROM uploader_marketorderlastupload h
        WHERE regionid = %s
          AND h.typeid = mo.typeid) AS age
FROM industry_wantedmarketorder mo
     INNER JOIN ccp.stastations st
       ON mo.stationid = st.stationid
     INNER JOIN ccp.mapsolarsystems sys
       ON st.solarsystemid = sys.solarsystemid
WHERE sys.regionid = %s
ORDER BY age DESC, typeid ASC
""",
              (regionid, regionid))
    want = set(typeid for (typeid, age) in c.fetchall()
               if age is None or age > 0)
    c.execute("""
(
SELECT typeid,
       (SELECT MIN(DATE_PART('days', (NOW() at time zone 'UTC')
                                      - h.cachetimestamp)) AS age
        FROM uploader_marketorderlastupload h
        WHERE regionid = %s
          AND h.typeid = t.typeid) AS age
FROM industry_pricelist t
UNION
SELECT typeid,
       (SELECT MIN(DATE_PART('days', (NOW() at time zone 'UTC')
                                      - h.cachetimestamp)) AS age
        FROM uploader_marketorderlastupload h
        WHERE regionid = %s
          AND h.typeid = t.typeid) AS age
FROM index_index t
WHERE NOT t.refineable
)
ORDER BY age DESC, typeid ASC
""", (regionid, regionid))
    rest = set(typeid for (typeid, age) in c.fetchall()
               if age is None or age > 0)
    result = (list(have) +
              list(want - have) +
              list(rest - want - have))
    return HttpResponse(json.dumps(result), content_type="text/json")

def order_age(regionid, typeid):
    today = datetime.datetime.utcnow()
    mo = MarketOrder.objects.filter(
        regionid=regionid, typeid=typeid
        ).aggregate(Max('cachetimestamp'))
    if mo['cachetimestamp__max'] is None:
        return 367 * 24
    else:
        delta = today - mo['cachetimestamp__max']
        return delta.days * 24 + (delta.seconds / 60.0 / 60.0)

@csrf_exempt
def json_suggest_corporations(request):
    current = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    c = connection.cursor()
    c.execute("SELECT corporationid "
              "FROM intel_corporation "
              "WHERE do_cache_check")
    result = set(corpid for (corpid,) in c.fetchall())
    # Current Amarr corps
    c.execute("SELECT corporationid "
              "FROM intel_corporation c "
              "     INNER JOIN intel_faction f "
              "       ON c.faction_id = f.id "
              "WHERE c.corporationid >= 98000000 "
              "  AND f.name = 'Amarr Empire' "
              "  AND (lastcache IS NULL OR lastcache < %s) "
              "ORDER BY lastcache ASC",
              (current,))
    result.update(corpid for (corpid,) in c.fetchall())
    # Other FW corps
    c.execute("SELECT corporationid "
              "FROM intel_corporation c "
              "     INNER JOIN intel_faction f "
              "       ON c.faction_id = f.id "
              "WHERE c.corporationid >= 98000000 "
              "  AND f.name != 'Amarr Empire' "
              "  AND (lastcache IS NULL OR lastcache < %s) "
              "ORDER BY lastcache ASC",
              (current,))
    result.update(corpid for (corpid,) in c.fetchall())
    # Former Amarr corps
    c.execute("SELECT corporationid "
              "FROM intel_corporation c "
              "WHERE c.corporationid >= 98000000 " # Not NPC
              "  AND EXISTS (SELECT * "
              "              FROM uploader_corpfactionhistory h "
              "              WHERE h.corporationid = c.corporationid "
              "                AND h.factionid = 500003 "
              "             ) "
              "AND c.lastcache < %s "
              "ORDER BY c.lastcache ASC",
              (current,))
    result.update(corpid for (corpid,) in c.fetchall())
    return HttpResponse(json.dumps(list(result)),
                        content_type="text/json")

from functools import wraps

def jsonrpc(func):
    @wraps(func)
    def wrapper(request):
        if request.method != 'POST':
            return HttpResponse('You seem to be lost.',
                                content_type='text/plain')
        try:
            args = json.loads(request.raw_post_data)
        except:
            return HttpResponse(json.dumps({'error': 'Malformed JSON args'}),
                                content_type='text/json')
        auth_token = args.get('auth_token')
        if auth_token is None:
            token = None
            user = None
        else:
            try:
                token = AuthToken.objects.get(tokenstring=auth_token)
            except AuthToken.DoesNotExist:
                token = None
                user = None
            else:
                if (token.user.profile and
                    token.user.profile.characterid is not None):
                    # Authenticated!
                    user = token.user
                else:
                    user = None
        try:
            return HttpResponse(json.dumps({'result': func(user, args)}),
                                content_type='text/json')
        except RPCError as e:
            return HttpResponse(json.dumps({'error': str(e)}),
                                content_type='text/json')
    return csrf_exempt(wrapper)

@csrf_exempt
def json_rpc(request):
    return HttpResponse(json.dumps({'error': 'Outdated RPC interface, update client'}),
                        content_type="text/json")

@jsonrpc
def json_check_auth_token(user, args):
    if user is None:
        return False
    return {'characterid': user.profile.characterid,
            'username': user.profile.name}

@jsonrpc
def json_submit_exception(user, args):
    mail_admins("[GDU] %s" % args['description'],
                "User: %s\nDescription: %s\n\n%s" %
                (user.profile.name,
                 args['description'],
                 args['trace']))
    return True

@jsonrpc
def json_submit_cache_data(user, args):
    if user is None:
        raise RPCError('Bad authentication token')
    func = EVERPC_METHODS.get(args.get('method'))
    if func is None:
        raise RPCError('Unknown cache data')
    func(user, args)
    return True

class RPCError(Exception):
    pass

##################################################################
# Data upload

def everpc_GetCorporationWarFactionID(user, args):
    cachetimestamp = wintime_to_datetime(args['timestamp'])
    upload = Upload.objects.create(user=user,
                                   cachetimestamp=cachetimestamp,
                                   method='facWarMgr.GetCorporationWarFactionID\
')
    corpid = args['corpid']
    factionid = args['factionid']

    if factionid > 0:
        faction = Faction.objects.get(factionid=factionid)
    else:
        faction = None
    corp, created = Corporation.objects.get_or_create(
        corporationid=corpid)
    corp.update_intel(cachetimestamp,
                      faction=faction,
                      lastcache=cachetimestamp)

    cfh, created = CorpFactionHistory.objects.get_or_create(
        corporationid=corpid,
        endtimestamp=None,
        defaults={'factionid': factionid,
                  'starttimestamp': cachetimestamp})
    cfh.uploads.add(upload)
    if (not created and
        cfh.starttimestamp < cachetimestamp and
        cfh.factionid != factionid):

        cfh.endtimestamp = cachetimestamp
        cfh.save()
        cfh2 = CorpFactionHistory.objects.create(
            corporationid=corpid,
            factionid=factionid,
            starttimestamp=cachetimestamp,
            endtimestamp=None)
        cfh2.uploads.add(upload)

def everpc_GetOldPriceHistory(user, args):
    cachetimestamp = wintime_to_datetime(args['timestamp'])
    upload = Upload.objects.create(user=user,
                                   cachetimestamp=cachetimestamp,
                                   method='marketProxy.GetOldPriceHistory')
    regionid = args['regionid']
    typeid = args['typeid']
    obj, created = MarketHistoryLastUpload.objects.get_or_create(
        regionid=regionid,
        typeid=typeid,
        defaults={'cachetimestamp': cachetimestamp})
    if not created and cachetimestamp > obj.cachetimestamp:
        obj.cachetimestamp = cachetimestamp
        obj.save()
    for row in args['history']:
        historydate = wintime_to_datetime(row['historyDate']).date()
        obj, created = MarketHistory.objects.get_or_create(
            regionid=regionid,
            typeid=typeid,
            historydate=historydate,
            defaults={'upload': upload,
                      'cachetimestamp': cachetimestamp,
                      'lowprice': row['lowPrice'],
                      'highprice': row['highPrice'],
                      'avgprice': row['avgPrice'],
                      'volume': row['volume'],
                      'orders': row['orders']
                      })

def everpc_GetOrders(user, args):
    cachetimestamp = wintime_to_datetime(args['timestamp'])
    upload = Upload.objects.create(user=user,
                                   cachetimestamp=cachetimestamp,
                                   method='marketProxy.GetOrders')
    typeid = args['typeid']
    regionid = args['regionid']
    obj, created = MarketOrderLastUpload.objects.get_or_create(
        regionid=regionid,
        typeid=typeid,
        defaults={'cachetimestamp': cachetimestamp})
    if not created and cachetimestamp > obj.cachetimestamp:
        obj.cachetimestamp = cachetimestamp
        obj.save()

    qs = MarketOrder.objects.filter(typeid=typeid, regionid=regionid)
    try:
        mo = qs[0]
    except IndexError:
        pass
    else:
        if mo.cachetimestamp > cachetimestamp:
            return
    qs.delete()
    for order in args['orders']:
        MarketOrder.objects.create(
            upload=upload,
            cachetimestamp=cachetimestamp,
            orderid=order['orderID'],
            stationid=order['stationID'],
            solarsystemid=order['solarSystemID'],
            regionid=regionid,
            volentered=order['volEntered'],
            volremaining=order['volRemaining'],
            minvolume=order['minVolume'],
            typeid=typeid,
            range=order['range'],
            duration=order['duration'],
            price=order['price'],
            bid=bool(order['bid']),
            issuedate=wintime_to_datetime(order['issueDate'])
            )

def everpc_GetVictoryPoints(user, args):
    pass

def everpc_GetFacWarData(user, args):
    cachetimestamp = wintime_to_datetime(args['timestamp'])
    upload = Upload.objects.create(user=user,
                                   cachetimestamp=cachetimestamp,
                                   method='map.GetVictoryPoints')
    for row in args['map']:
        if row['factionid'] is None:
            c = connection.cursor()
            c.execute("SELECT COALESCE(s.factionid, c.factionid, r.factionid) "
                      "FROM ccp.mapsolarsystems s "
                      "     INNER JOIN ccp.mapconstellations c "
                      "       ON s.constellationid = c.constellationid "
                      "     INNER JOIN ccp.mapregions r "
                      "       ON c.regionid = r.regionid "
                      "WHERE s.solarsystemid = %s", (row['systemid'],))
            row['factionid'] = c.fetchone()[0]
        if not FacWarSystemHistory.objects.filter(
            cachetimestamp=cachetimestamp).exists():
            # Not known yet
            FacWarSystemHistory.objects.create(
                upload=upload,
                cachetimestamp=cachetimestamp,
                solarsystemid=row['systemid'],
                occupyingfactionid=row['factionid'],
                victorypoints=row['current'],
                threshold=row['threshold']
                )
        obj, created = FacWarSystem.objects.get_or_create(
            solarsystemid=row['systemid'],
            defaults={'upload': upload,
                      'cachetimestamp': cachetimestamp,
                      'solarsystemid': row['systemid'],
                      'solarsystemname': '',
                      'occupyingfactionid': row['factionid'],
                      'occupyingfactionname': '',
                      'owningfactionid': 0,
                      'owningfactionname': '',
                      'victorypoints': row['current'],
                      'threshold': row['threshold']
                      })
        if created:
            obj.solarsystemname = dbutils.get_itemname(obj.solarsystemid)
            obj.occupyingfactionname = dbutils.get_itemname(
                obj.occupyingfactionid)
            obj.owningfactionid = dbutils.get_systemfaction(obj.solarsystemid)
            obj.owningfactionname = dbutils.get_itemname(obj.owningfactionid)
        elif cachetimestamp > obj.cachetimestamp:
            obj.cachetimestamp = cachetimestamp
            obj.occupyingfactionid = row['factionid']
            obj.occupyingfactionname = dbutils.get_itemname(row['factionid'])
            obj.threshold = row['threshold']
            obj.victorypoints = row['current']
            obj.save()

def everpc_LookupCharacters(user, args):
    for charid in args['ids']:
        Pilot.objects.get_or_create(characterid=charid)


EVERPC_METHODS = {
    'facWarMgr.GetCorporationWarFactionID': everpc_GetCorporationWarFactionID,
    'marketProxy.GetOldPriceHistory': everpc_GetOldPriceHistory,
    'marketProxy.GetOrders': everpc_GetOrders,
    'map.GetVictoryPoints': everpc_GetVictoryPoints,
    'map.GetFacWarData': everpc_GetFacWarData,
    'lookupSvc.LookupCharacters': everpc_LookupCharacters,
}

def wintime_to_datetime(timestamp):
    return datetime.datetime.utcfromtimestamp(
        (timestamp - 116444736000000000L) / 10000000
        )
