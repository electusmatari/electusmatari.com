import datetime
import json

from django.contrib import messages
from django.db import connection, IntegrityError, transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic.list_detail import object_list
from django.views.generic.simple import direct_to_template

from gradient.decorators import require_gradient
from gradient.rc.models import Change
from gradient.industry.models import PriceList, BlueprintOriginal
from gradient.industry.models import Stock, StockLevel, Transaction
from gradient.industry.models import MarketOrder, WantedMarketOrder
from gradient.industry.models import LastUpdate
from gradient.dbutils import get_typeid, get_typename, get_itemname
from gradient.dbutils import get_membername, get_itemid
from gradient.industry.utils import last_price, get_component_list
from gradient.industry.forms import WantedMarketOrderForm, StockLevelForm
from gradient.industry.forms import BlueprintOriginalForm

from emtools.ccpeve.models import APIKey

@require_gradient
def overview(request):
    if request.method == 'POST':
        return overview_post(request)
    station_dict = {}
    for wmo in WantedMarketOrder.objects.filter(forcorp=True):
        station_dict.setdefault(wmo.stationname, [])
        station_dict[wmo.stationname].append(wmo)
    return direct_to_template(
        request, 'industry/overview.html',
        extra_context={'station_list': sorted(station_dict.items())})

def overview_post(request):
    action = request.POST.get('action')
    wmo = get_object(WantedMarketOrder, pk=request.POST.get('wmoid'))
    if wmo is None:
        messages.add_message(request, messages.ERROR,
                             'Bad wmoid, stop tampering')
    elif action == 'drop':
        if wmo.characterid == request.user.profile.characterid:
            wmo.characterid = None
            wmo.charactername = None
            wmo.save()
            messages.add_message(request, messages.SUCCESS,
                                 'You relinquished the order for %s' %
                                 wmo.typename)
            if wmo.forcorp:
                Change.objects.create(app='industry',
                                      category='order',
                                      text=('%s stopped handling the orders '
                                            'for %s at %s' %
                                            (request.user.profile.name,
                                             wmo.typename,
                                             wmo.stationname)))
        else:
            messages.add_message(request, messages.ERROR,
                                 "That is not your order")
    elif action == 'accept':
        if wmo.characterid is None:
            wmo.characterid = request.user.profile.characterid
            wmo.charactername = request.user.profile.name
            wmo.save()
            messages.add_message(request, messages.SUCCESS,
                                 'You are now handling the the order for %s' %
                                 wmo.typename)
            if wmo.forcorp:
                Change.objects.create(app='industry',
                                      category='order',
                                      text=('%s is now handling the orders '
                                            'for %s at %s' %
                                            (request.user.profile.name,
                                             wmo.typename,
                                             wmo.stationname)))
        else:
            messages.add_message(request, messages.ERROR,
                                 "That order is already taken")
    return HttpResponseRedirect('/industry/')

@require_gradient
def prices_view(request):
    lu = LastUpdate.objects.get(name='pricelist').timestamp
    prices = []
    for price in PriceList.objects.all():
        prices.append({'name': price.typename,
                       'type': price.typename,
                       'value': price.productioncost * price.safetymargin})
    return direct_to_template(request, 'industry/prices.html',
                              extra_context={'jsondata': json.dumps(prices),
                                             'lastupdate': lu})

@require_gradient
def build_view(request, typename):
    component_list = get_component_list(typename)
    return direct_to_template(request, 'industry/component_list.html',
                              extra_context={'typename': typename,
                                             'component_list': component_list})

@require_gradient
def marketorders_view(request):
    lu = LastUpdate.objects.get(name='marketorders').timestamp
    order_set = MarketOrder.objects.all()
    wanted_set = WantedMarketOrder.objects.all()
    pilot_name = None
    if request.GET.get('all') is None:
        pilot_name = request.user.profile.name
        order_set = order_set.filter(
            characterid=request.user.profile.characterid)
        wanted_set = wanted_set.filter(
            characterid=request.user.profile.characterid)
    order_dict = {}
    for order in order_set:
        order.station = get_itemname(order.stationid)
        order.typename = get_typename(order.typeid)
        ordertype = order.ordertype
        order_dict.setdefault(order.station, {})
        order_dict[order.station].setdefault(ordertype, [])
        order_dict[order.station][ordertype].append(order)
        if pilot_name is None:
            order.pilotname = get_membername(order.characterid)
        if request.GET.get('all') is None:
            equal = MarketOrder.objects.filter(stationid=order.stationid,
                                               typeid=order.typeid,
                                               ordertype=order.ordertype)
            equal = equal.exclude(
                characterid=request.user.profile.characterid)
            order.othercorp = [get_membername(other.characterid)
                               for other in equal]
    for wanted in wanted_set:
        station = get_itemname(wanted.stationid)
        typename = get_typename(wanted.typeid)
        ordertype = wanted.ordertype
        order_dict.setdefault(station, {})
        order_dict[station].setdefault(ordertype, [])
        if wanted.typeid not in [order.typeid
                                 for order in order_dict[station][ordertype]]:
            try:
                pl = PriceList.objects.get(typeid=wanted.typeid)
            except PriceList.DoesNotExist:
                productioncost = 0.0
            else:
                productioncost = pl.productioncost * pl.safetymargin

            price = last_price(ordertype,
                               wanted.stationid,
                               wanted.typeid)
            if ordertype == 'sell':
                if price == 0:
                    profitmargin = 0
                else:
                    profitmargin = 1 - (productioncost / price)
                profitperitem = price - productioncost
            else:
                if price == 0:
                    profitmargin = 0
                else:
                    profitmargin = (productioncost - price) / price
                profitperitem = productioncost - price
            order = KeyValue(stationid=wanted.stationid,
                             stationname=station,
                             typeid=wanted.typeid,
                             typename=typename,
                             ordertype=ordertype,
                             expires=datetime.datetime(2000, 1, 1),
                             volremaining=0,
                             price=price,
                             productioncost=productioncost,
                             salesperday=0.0,
                             trend=0.0,
                             expiredays=0,
                             profitmargin=profitmargin,
                             profitperitem=profitperitem,
                             daysremaining=0,
                             profitperday=0,
                             )
            order_dict[station][ordertype].append(order)
            if request.GET.get('all') is None:
                equal = MarketOrder.objects.filter(stationid=order.stationid,
                                                   typeid=order.typeid,
                                                   ordertype=order.ordertype)
                equal = equal.exclude(
                    characterid=request.user.profile.characterid)
                order.othercorp = [get_membername(other.characterid)
                                   for other in equal]

    order_list = []
    for station, otypes in order_dict.items():
        newotypes = {}
        for ordertype, orders in otypes.items():
            newotypes[ordertype] = sorted(orders, key=lambda o: o.typename)
        order_list.append((station, newotypes))
    return direct_to_template(
        request, 'industry/marketorders.html',
        extra_context={'pilot_name': pilot_name,
                       'order_list': order_list,
                       'lastupdate': lu})

@require_gradient
def marketorders_edit(request, orderid=None):
    if orderid is None:
        instance = None
        forcorp = False
    else:
        instance = get_object_or_404(WantedMarketOrder, pk=orderid)
        forcorp = instance.forcorp
    if request.method == 'POST':
        form = WantedMarketOrderForm(request.POST, instance=instance)
        if form.is_valid():
            wmo = form.save(commit=False)
            wmo.characterid = request.user.profile.characterid
            wmo.charactername = request.user.profile.name
            wmo.stationid = get_itemid(wmo.stationname)
            wmo.typeid = get_typeid(wmo.typename)
            wmo.save()
            messages.add_message(request, messages.SUCCESS,
                                 'Order requests updated')
            if wmo.forcorp or forcorp:
                Change.objects.create(app='industry',
                                      category='order',
                                      text=('%s edited the order for '
                                            '%s at %s' %
                                            (request.user.profile.name,
                                             wmo.typename,
                                             wmo.stationname)))
            return HttpResponseRedirect('/industry/marketorders/config/')
    else:
        form = WantedMarketOrderForm(instance=instance)
    return direct_to_template(request, 'industry/marketconfig_edit.html',
                              extra_context={'form': form,
                                             'instance': instance})

@require_gradient
def marketorders_delete(request, orderid):
    instance = get_object_or_404(WantedMarketOrder, pk=orderid)
    if request.method == 'POST':
        if instance.forcorp:
            Change.objects.create(app='industry',
                                  category='order',
                                  text=('%s deleted the order for '
                                        '%s at %s' %
                                        (request.user.profile.name,
                                         instance.typename,
                                         instance.stationname)))
        instance.delete()
        messages.add_message(request, messages.SUCCESS,
                             'Order request deleted')
        return HttpResponseRedirect('/industry/marketorders/config/')
    else:
        return direct_to_template(request, 'industry/marketconfig_delete.html',
                                  extra_context={'instance': instance})

@require_gradient
def config_view(request):
    if request.GET.get('all', False):
        wmo_list = WantedMarketOrder.objects.all()
    else:
        wmo_list = WantedMarketOrder.objects.filter(
            characterid=request.user.profile.characterid,
            forcorp=False)
    return direct_to_template(request, 'industry/config.html',
                              extra_context={'wanted_list': wmo_list})

@require_gradient
def stocks_view(request, watched=False):
    lu = LastUpdate.objects.get(name='stocks').timestamp
    stock_dict = {}
    if watched:
        qs = request.user.stocklevel_set.all()
    else:
        qs = StockLevel.objects.all()
    for stock in qs:
        station = get_itemname(stock.stationid)
        stock_dict.setdefault(station, [])
        stock_dict[station].append(stock)
    return direct_to_template(request, 'industry/stocks.html',
                              extra_context={'lastupdate': lu,
                                             'watched': watched,
                                             'station_list': sorted(stock_dict.items())})

@require_gradient
def stocks_edit(request, stockid=None):
    if stockid is None:
        instance = None
        oldhigh = None
    else:
        instance = get_object_or_404(StockLevel, pk=stockid)
        oldhigh = instance.high
    if request.method == 'POST':
        form = StockLevelForm(request.POST, instance=instance)
        if form.is_valid():
            sl = form.save(commit=False)
            sl.stationid = get_itemid(sl.stationname)
            sl.typeid = get_typeid(sl.typename)
            try:
                sl.save()
            except IntegrityError:
                transaction.rollback()
                messages.add_message(request, messages.ERROR,
                                     'Stock level already exists')
                return HttpResponseRedirect('/industry/stocks/')
            try:
                st = Stock.objects.get(typeid=sl.typeid,
                                       stationid=sl.stationid)
            except Stock.DoesNotExist:
                pass
            else:
                st.level = sl
                st.save()
            Change.objects.create(app='industry',
                                  category='stocks',
                                  text=('%s updated the stock level for %s '
                                        'at %s from %s to %s' %
                                        (request.user.profile.name,
                                         sl.typename,
                                         sl.stationname,
                                         oldhigh,
                                         sl.high)))
            messages.add_message(request, messages.SUCCESS,
                                 'Stock level updated')
            return HttpResponseRedirect('/industry/stocks/')
    else:
        form = StockLevelForm(instance=instance)
    return direct_to_template(request, 'industry/stocks_edit.html',
                              extra_context={'form': form,
                                             'instance': instance})

@require_gradient
def stocks_delete(request, stockid):
    instance = get_object_or_404(StockLevel, pk=stockid)
    if request.method == 'POST':
        Change.objects.create(app='industry',
                              category='stocks',
                              text=('%s deleted the stock level for %s '
                                    'at %s' %
                                    (request.user.profile.name,
                                     instance.typename,
                                     instance.stationname)))
        instance.level = None
        instance.price = None
        instance.delete()
        messages.add_message(request, messages.SUCCESS,
                             'Stock level request deleted')
        return HttpResponseRedirect('/industry/stocks/')
    else:
        return direct_to_template(request, 'industry/stocks_delete.html',
                                  extra_context={'instance': instance})

@require_gradient
def stocks_watch(request, stockid):
    instance = get_object_or_404(StockLevel, pk=stockid)
    instance.watcher.add(request.user)
    return HttpResponseRedirect('/industry/stocks/')

@require_gradient
def stocks_unwatch(request, stockid):
    instance = get_object_or_404(StockLevel, pk=stockid)
    instance.watcher.remove(request.user)
    return HttpResponseRedirect('/industry/stocks/watched/')

@require_gradient
def profitability(request):
    c = connection.cursor()
    c.execute("SELECT pl.typename, pl.productioncost, pl.safetymargin, "
              "       mp.price, "
              "       mp.price - (pl.productioncost * pl.safetymargin) "
              "         as profit "
              "FROM industry_pricelist pl "
              "     INNER JOIN industry_marketprice mp "
              "       ON pl.typeid = mp.typeid "
              "ORDER BY profit DESC")
    products = [dict(typename=typename, productioncost=productioncost,
                     safetymargin=safetymargin, marketprice=marketprice,
                     profit=profit)
                for (typename, productioncost, safetymargin,
                    marketprice, profit) in c.fetchall()]
    return direct_to_template(request, 'industry/profitability.html',
                              extra_context={'product_list': products})

@require_gradient
def bpos_view(request):
    bpos = BlueprintOriginal.objects.all()
    return direct_to_template(request, 'industry/bpos.html',
                              extra_context={'bpo_list': bpos})

@require_gradient
def bpos_edit(request, bpoid=None):
    if bpoid is None:
        instance = None
    else:
        instance = get_object_or_404(BlueprintOriginal, pk=bpoid)
    if request.method == 'POST':
        form = BlueprintOriginalForm(request.POST, instance=instance)
        if form.is_valid():
            bpo = form.save(commit=False)
            bpo.typeid = get_typeid(bpo.typename)
            bpo.save()
            Change.objects.create(app='industry',
                                  category='bpos',
                                  text=('%s edited the %s' %
                                        (request.user.profile.name,
                                         bpo.typename)))
            messages.add_message(request, messages.SUCCESS,
                                 'BPO saved')
            return HttpResponseRedirect('/industry/bpos/')
    else:
        form = BlueprintOriginalForm(instance=instance)
    return direct_to_template(request, 'industry/bpos_edit.html',
                              extra_context={'form': form,
                                             'instance': instance})

@require_gradient
def bpos_delete(request, bpoid):
    instance = get_object_or_404(BlueprintOriginal, pk=bpoid)
    if request.method == 'POST':
        Change.objects.create(app='industry',
                              category='bpos',
                              text=('%s deleted the %s' %
                                    (request.user.profile.name,
                                     instance.typename)))
        instance.delete()
        messages.add_message(request, messages.SUCCESS,
                             'Blueprint original deleted')
        return HttpResponseRedirect('/industry/bpos/')
    else:
        return direct_to_template(request, 'industry/bpos_delete.html',
                                  extra_context={'instance': instance})

@require_gradient
def bpos_update(request):
    if request.method == 'POST':
        grd = APIKey.objects.get(name='Gradient').corp()
        api_bps = grd.Blueprints()
        for api_bp in api_bps:
            if api_bp.quantity == -1:
                # it's an unstacked BPO
                try:
                    bpo = BlueprintOriginal.objects.get(typename=api_bp.typename)
                    api_me = api_bp.materialEfficiency
                    # references to PE here need to change to TE when I change them elsewhere
                    api_pe = api_bp.timeEfficency
                    if api_me != bpo.me or api_pe != bpo.pe:
                        messages.add_message(request, messages.ERROR,
                                             '%s in hangar has ME/PE %d/%d, database says %d/%d' %
                                             bpo.typename, api_me, api_pe, bpo.me, bpo.pe)
                except BlueprintOriginal.DoesNotExist:
                    messages.add_message(request, messages.ERROR,
                                         '%s is available but not in the database' %
                                         api_bp.typename)
        for bpo in BlueprintOriginal.objects.all():
            bpo_found = False
            for api_bp in api_bps:
                if bpo.typeid == api_bp.typeid and api_bp.quantity == -1:
                    bpo_found = True
                    break
            if not bpo_found:
                messages.add_message(request, messages.ERROR,
                                     '%s is in the database but we do not own it' %
                                     bpo.typename)
        Change.objects.create(app='industry',
                              category='bpos',
                              text=('%s ran BPO auto-update' %
                                    (request.user.profile.name)))
        messages.add_message(request, messages.SUCCESS,
                             'BPO inventory updated (TODO: not really updated)')
        return HttpResponseRedirect('/industry/bpos/')
    else:
        return direct_to_template(request, 'industry/bpos_update.html')

@require_gradient
def transactions_view(request):
    if 'all' in request.GET:
        display_pilot = True
        qs = Transaction.objects.all()
    else:
        display_pilot = False
        qs = Transaction.objects.filter(
            characterid=request.user.profile.characterid
            )
    return object_list(request,
                       queryset=qs,
                       paginate_by=20,
                       template_object_name='transaction',
                       template_name='industry/transactions.html',
                       extra_context={
            'display_pilot': display_pilot,
            'request': request,
            })

@require_gradient
def json_invtype(request):
    term = request.GET.get('term', '')
    if len(term) < 3:
        lis = []
    else:
        c = connection.cursor()
        c.execute("SELECT typename FROM ccp.invtypes "
                  "WHERE typename ILIKE %s AND published = 1 "
                  "ORDER BY typename ASC",
                  ("%%%s%%" % term,))
        lis = [name for (name,) in c.fetchall()]
    return HttpResponse(json.dumps(lis), mimetype="text/plain")

@require_gradient
def json_blueprint(request):
    term = request.GET.get('term', '')
    if len(term) < 3:
        lis = []
    else:
        c = connection.cursor()
        c.execute("SELECT t.typename "
                  "FROM ccp.invblueprinttypes b "
                  "     INNER JOIN ccp.invtypes t "
                  "       ON b.blueprinttypeid = t.typeid "
                  "WHERE t.published = 1 "
                  "  AND t.marketgroupid IS NOT NULL "
                  "  AND t.typename ILIKE %s "
                  "ORDER BY t.typename ASC",
                  ("%%%s%%" % term,))
        lis = [name for (name,) in c.fetchall()]
    return HttpResponse(json.dumps(lis), mimetype="text/plain")

@require_gradient
def json_station(request):
    term = request.GET.get('term', '')
    if len(term) < 3:
        lis = []
    else:
        c = connection.cursor()
        c.execute("SELECT stationname FROM ccp.stastations "
                  "WHERE stationname ILIKE %s "
                  "ORDER BY stationname ASC",
                  ("%%%s%%" % term,))
        lis = [name for (name,) in c.fetchall()]
    return HttpResponse(json.dumps(lis), mimetype="text/plain")

def get_object(cls, **kwargs):
    try:
        return cls.objects.get(**kwargs)
    except cls.DoesNotExist:
        return None

class KeyValue(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
