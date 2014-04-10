import datetime
import json
import re
from functools import wraps

from emtools.ccpeve.models import apiroot, APIKey

from django.contrib import messages
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.db import connection
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.simple import direct_to_template
from django.views.generic.list_detail import object_list

from gradient.decorators import require_gradient
from gradient.shop.models import SalesOffice, ProductList, Order, Message
from gradient.shop.models import OrderHandler


def require_auth(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        shopuser = ShopUser.from_request(request)
        if shopuser.characterid is None:
            return HttpResponseRedirect('/shop/auth/?next=%s' %
                                        (request.get_full_path(),))
        else:
            return func(request, *args, **kwargs)
    return wrapper

##################################################################
# Shop index / search

def index_view(request):
    shopuser = ShopUser.from_request(request)
    shopinfo = ShopInfo()
    context = {'shopinfo': shopinfo,
               'shopuser': shopuser}
    if request.method == 'POST':
        return add_to_cart(request, shopuser)
    context['needle'] = request.GET.get('search', None)
    if context['needle'] is None:
        context['needle'] = ""
        context['product_list'] = top_3()
        context['indexpage'] = True
    else:
        objects = ProductList.objects.filter(
            typename__icontains=context['needle'])
        paginator = Paginator(objects, 5)
        try:
            pagenum = int(request.GET.get('page', 1))
        except ValueError:
            pagenum = 1
        try:
            page = paginator.page(pagenum)
        except (EmptyPage, InvalidPage):
            page = paginator.page(paginator.num_pages)
        context['page'] = page
        context['product_list'] = page.object_list
    for product in context['product_list']:
        product.multiplier = shopuser.multiplier
        product.discount = shopuser.discount
    return direct_to_template(request, 'shop/index.html',
                              extra_context=context)

def add_to_cart(request, shopuser):
    next_url = request.POST.get('next', '/shop/')
    if request.POST.get('typeid', None) == "shipfit":
        shipfit = request.POST["shipfit"]
        for line in shipfit.splitlines():
            line = line.strip()
            if not line:
                continue
            # [Stabber Fleet Issue, DualProp Buffer]
            m = re.match(r'^\[(.*?),.*$', line)
            if m is not None:
                itemtype = m.group(1)
                try:
                    product = ProductList.objects.get(typename=itemtype)
                except ProductList.DoesNotExist:
                    messages.add_message(request, messages.ERROR,
                                         "Can't find {}"
                                         .format(itemtype))
                    continue
                shopuser.add(product.typeid, 1)
                continue
            #  Valkyrie II x4
            #  Heavy Assault Missile Launcher II, Scourge Heavy Assault Missile
            m = re.match(r'^(.+?)(?:\s+x([0-9]+))?(?:,\s+(.+))?$', line)
            if m is not None:
                itemtype, qty, ammo = m.groups()
                # we could guess how much ammo they want, but for now, don't
                if qty is None:
                    qty = 1
                try:
                    product = ProductList.objects.get(typename=itemtype)
                except ProductList.DoesNotExist:
                    messages.add_message(request, messages.ERROR,
                                         "Can't find {}"
                                         .format(itemtype))
                    continue
                shopuser.add(product.typeid, int(qty))
        shopuser.save(request)
        return HttpResponseRedirect(next_url)
    try:
        typeid = int(request.POST.get('typeid', None))
        qty = int(request.POST.get('quantity', None))
    except ValueError:
        return HttpResponseRedirect(next_url)
    try:
        ProductList.objects.get(typeid=typeid)
    except ProductList.DoesNotExist:
        return HttpResponseRedirect(next_url)
    shopuser.add(typeid, qty)
    shopuser.save(request)
    return HttpResponseRedirect(next_url)

##################################################################
# Cart checkout

@require_auth
def cart_view(request):
    shopuser = ShopUser.from_request(request)
    shopinfo = ShopInfo()
    context = {'shopinfo': shopinfo,
               'shopuser': shopuser}
    if request.method == 'POST':
        return cart_post(request, shopuser)
    cart_products = []
    total = 0
    for typeid, qty in shopuser.cart.items():
        try:
            product = ProductList.objects.get(typeid=typeid)
            grdprice = product.grdprice
            cart_products.append((product, grdprice, qty, grdprice * qty))
            total += grdprice * qty
        except ProductList.DoesNotExist:
            shopuser.set(typeid, 0)
            continue
    cart_products.sort(key=lambda x: x[0].typename)
    context['cart_products'] = cart_products
    context['total'] = total
    return direct_to_template(request, 'shop/cart.html',
                              extra_context=context)

def cart_post(request, shopuser):
    action = request.POST.get('action', None)
    if action == 'change_quantities':
        for name, qty in request.POST.items():
            if name.startswith('qty'):
                try:
                    typeid = int(name[3:])
                    qty = int(qty)
                except:
                    pass
                else:
                    shopuser.set(typeid, qty)
        shopuser.save(request)
        return HttpResponseRedirect('/shop/cart/')
    elif action == 'confirm_order':
        try:
            salespoint = SalesOffice.objects.get(
                pk=request.POST.get('salespoint', 1))
        except (SalesOffice.DoesNotExist, ValueError):
            salespoint = SalesOffice.objects.get(name='Pator')
        for typeid, qty in shopuser.cart.items():
            try:
                product = ProductList.objects.get(typeid=typeid)
            except ProductList.DoesNotExist:
                shopuser.set(typeid, 0)
                continue
            Order.objects.create(
                # Customer
                characterid=shopuser.characterid,
                name=shopuser.name,
                corpid=shopuser.corpid,
                corpname=shopuser.corpname,
                allianceid=shopuser.allianceid,
                alliancename=shopuser.alliancename,
                standing=shopuser.standing,
                discount=shopuser.discount or "",
                lastchecked=shopuser.lastchecked,
                # Product
                typeid=typeid,
                typename=product.typename,
                quantity=qty,
                price=product.productioncost * product.safetymargin,
                multiplier=shopuser.multiplier,
                # Location
                office=salespoint,
                # Order
                handler=None,
                closed=None,
                cancelled=False)
            shopuser.set(typeid, 0)
        shopuser.save(request)
        return HttpResponseRedirect('/shop/order/')
    return HttpResponseRedirect('/shop/cart/')

##################################################################
# Customer's order view

@require_auth
def order_view(request):
    shopuser = ShopUser.from_request(request)
    shopinfo = ShopInfo()
    context = {'shopinfo': shopinfo,
               'shopuser': shopuser}
    if request.method == 'POST':
        return order_post(request, shopuser)
    offices = {}
    per_office = {}
    for order in Order.objects.filter(characterid=shopuser.characterid,
                                      closed=None):
        offices[order.office.id] = order.office
        per_office.setdefault(order.office.id, [])
        per_office[order.office.id].append(order)
    full_list = per_office.items()
    full_list.sort()
    context['full_list'] = [(offices[id], order_list,
                             sum(o.price_total for o in order_list))
                            for (id, order_list) in full_list]
    context['total'] = sum(office_total for (office, order_list, office_total)
                           in context['full_list'])
    old_list = Order.objects.filter(
        characterid=shopuser.characterid
        ).exclude(
        closed=None
        ).filter(
        closed__gt=(datetime.datetime.utcnow() -
                    datetime.timedelta(days=28))
        ).order_by('-closed')
    context['old_list'] = old_list
    return direct_to_template(request, 'shop/order.html',
                              extra_context=context)

def order_post(request, shopuser):
    order = get_object_or_404(Order, pk=request.POST.get('orderid'))
    if order.characterid != shopuser.characterid:
        raise Http404
    order.cancelled = True
    order.closed = datetime.datetime.utcnow()
    order.save()
    return HttpResponseRedirect('/shop/order/')

##################################################################
# Customer messages view

@require_auth
def messages_view(request):
    shopuser = ShopUser.from_request(request)
    shopinfo = ShopInfo()
    context = {'shopinfo': shopinfo,
               'shopuser': shopuser}
    if request.method == 'POST':
        Message.objects.create(
            characterid=shopuser.characterid,
            name=shopuser.name,
            read_by_customer=True,
            read_by_handler=False,
            handler=None,
            text=request.POST.get('text', '')
            )
        return HttpResponseRedirect('/shop/messages/')
    message_list = Message.objects.filter(characterid=shopuser.characterid)
    paginator = Paginator(message_list, 10)
    try:
        pagenum = int(request.GET.get('page', None))
    except (ValueError, TypeError):
        pagenum = paginator.num_pages
    try:
        page = paginator.page(pagenum)
    except (EmptyPage, InvalidPage):
        page = paginator.page(paginator.num_pages)
    context['is_paginated'] = True
    context['page_obj'] = page
    context['message_list'] = page.object_list
    for message in page.object_list:
        message.read_by_customer = True
        message.save()
    return direct_to_template(request, 'shop/messages.html',
                              extra_context=context)

##################################################################
# Authentication

def auth_view(request):
    shopuser = ShopUser.from_request(request)
    shopinfo = ShopInfo()
    context = {'shopinfo': shopinfo,
               'shopuser': shopuser}

    if request.method == 'GET':
        context['next_url'] = request.GET.get('next', '/shop/')
        return direct_to_template(request, 'shop/auth.html',
                                  extra_context=context)
    # POST
    context['next_url'] = request.POST.get('next')
    keyid = request.POST.get('keyid')
    vcode = request.POST.get('vcode')
    characterid = request.POST.get('characterid')
    if keyid is None or vcode is None:
        return direct_to_template(request, 'shop/auth.html',
                                  extra_context=context)
    context['keyid'] = keyid
    context['vcode'] = vcode
    if 'grdshop' not in vcode:
        context['error'] = 'bad-vcode'
        return direct_to_template(request, 'shop/auth.html',
                                  extra_context=context)
    # Check API key
    api = apiroot()
    api = api.auth(keyID=keyid, vCode=vcode)
    try:
        keyinfo = api.account.APIKeyInfo()
    except Exception as e:
        context['error'] = 'api-error'
        context['message'] = ('Error %s during API call: %s' %
                              (e.__class__.__name__, str(e)))
        return direct_to_template(request, 'shop/auth.html',
                                  extra_context=context)
    context['characters'] = keyinfo.key.characters
    if len(keyinfo.key.characters) == 1:
        char = keyinfo.key.characters[0]
    elif len(keyinfo.key.characters) > 1 and characterid is None:
        return direct_to_template(request, 'shop/auth.html',
                                  extra_context=context)
    else:
        char = None
        for char_entry in keyinfo.key.characters:
            if str(char_entry.characterID) == characterid:
                char = char_entry
                break
        if char is None:
            context['error'] = 'char-not-found'
            return direct_to_template(request, 'shop/auth.html',
                                      extra_context=context)
    user = shopuser
    user.characterid = char.characterID
    user.name = char.characterName
    try:
        user.recheck()
    except Exception as e:
        context['error'] = 'api-error'
        context['message'] = ('Error %s during API call: %s' %
                              (e.__class__.__name__, str(e)))
        return direct_to_template(request, 'shop/auth.html',
                                  extra_context=context)
    request.session.set_expiry(60 * 60 * 24 * 365)
    user.save(request)
    return HttpResponseRedirect(context['next_url'])

##################################################################
# Handle active orders

@require_gradient
def handle_view(request):
    if request.method == 'POST':
        return handle_post(request)
    orderid_list = request.GET.getlist('orderid')
    if len(orderid_list) > 0:
        return handle_finalize(request, orderid_list)
    customer_orders = {}
    for order in Order.objects.filter(closed=None):
        customer_orders.setdefault(order.name, [])
        customer_orders[order.name].append(order)
    customer_list = []
    for name, order_list in customer_orders.items():
        order = order_list[0]
        characterid = order.characterid
        standing = order.standing_string()
        try:
            message = Message.objects.filter(characterid=characterid
                                             ).reverse()[0]
        except IndexError:
            message = None
        customer_list.append((name, characterid, standing, message,
                              order_list))
    customer_list.sort()
    return direct_to_template(request, 'shop/handle.html',
                              extra_context={'customer_list': customer_list})

def handle_finalize(request, orderid_list):
    order_list = []
    total = 0
    customer_total = 0
    characterid = None
    name = None
    standing = None
    for orderid in orderid_list:
        order = Order.objects.get(pk=orderid)
        if characterid is None:
            characterid = order.characterid
        elif characterid != order.characterid:
            messages.add_message(request, messages.ERROR,
                                 "Can't handle orders of different "
                                 "customers at once")
            return HttpResponseRedirect('/shop/handle/')
        name = order.name
        standing = order.standing_string()
        customer_total += order.price_total
        try:
            product = ProductList.objects.get(typeid=order.typeid)
        except ProductList.DoesNotExist:
            order.price = order.price
            order_list.append((order, None))
        else:
            order.price = product.grdprice
            order_list.append((order, product))
        total += order.price_total
    return direct_to_template(request, 'shop/handle_finalize.html',
                              extra_context={'order_list': order_list,
                                             'name': name,
                                             'standing': standing,
                                             'total': total,
                                             'customer_total': customer_total})

@require_gradient
@csrf_exempt
def handle_split(request):
    try:
        orderid = int(request.POST.get('orderid'))
        qty = int(request.POST.get('quantity'))
    except (ValueError, TypeError):
        return HttpResponse(json.dumps({'success': False,
                                        'error': 'Bad input'}),
                            mimetype='text/json')
    try:
        order = Order.objects.get(pk=orderid)
    except Order.DoesNotExist:
        return HttpResponse(json.dumps({'success': False,
                                        'error': 'Unknown orderid'}),
                            mimetype='text/json')
    if order.quantity <= qty:
        return HttpResponse(json.dumps({'success': False,
                                        'error': "You have to specify a quantity lower than the quantity of the order"}),
                            mimetype='text/json')
    if order.quantity <= 0:
        return HttpResponse(json.dumps({'success': False,
                                        'error': "You have to specify a quantity greater than zero"}),
                            mimetype='text/json')
    order2 = Order()
    order2.characterid = order.characterid
    order2.name = order.name
    order2.corpid = order.corpid
    order2.corpname = order.corpname
    order2.allianceid = order.allianceid
    order2.alliancename = order.alliancename
    order2.standing = order.standing
    order2.discount = order.discount
    order2.multiplier = order.multiplier
    order2.lastchecked = order.lastchecked
    order2.typeid = order.typeid
    order2.typename = order.typename
    order2.quantity = qty
    order2.price = order.price
    order2.office = order.office
    order2.handler = order.handler
    order2.closed = order.closed
    order2.cancelled = order.cancelled
    order2.save()
    order.quantity -= qty
    order.save()
    messages.add_message(request, messages.SUCCESS,
                         'Order split')
    return HttpResponse(json.dumps({'success': True}),
                        mimetype='text/json')

def handle_post(request):
    orderid_list = request.POST.getlist('orderid')
    for orderid in orderid_list:
        order = Order.objects.get(pk=orderid)
        order.handler = request.user
        order.closed = datetime.datetime.utcnow()
        order.save()
    messages.add_message(request, messages.SUCCESS,
                         'Order closed')
    return HttpResponseRedirect('/shop/handle/')

##################################################################
# Display closed orders

@require_gradient
def handle_closed_view(request):
    qs = Order.objects.exclude(closed=None).order_by("-closed")
    return object_list(request, qs,
                       paginate_by=30,
                       template_name='shop/handle_closed_orders.html',
                       template_object_name='order')

##################################################################
# Handler's view of messages

@require_gradient
def handle_messages_view(request, characterid=None):
    api = apiroot()
    if characterid is not None:
        name = api.eve.CharacterName(ids=characterid).characters[0].name
    else:
        name = None
    if request.method == 'POST':
        if characterid is not None:
            Message.objects.create(
                characterid=characterid,
                name=name,
                read_by_customer=False,
                read_by_handler=True,
                handler=request.user,
                text=request.POST.get('text', '')
            )
        return HttpResponseRedirect('/shop/handle/messages/%s/' % characterid)
    message_list = Message.objects.all()
    if characterid is not None:
        message_list = message_list.filter(characterid=characterid)
    paginator = Paginator(message_list, 10)
    try:
        pagenum = int(request.GET.get('page', None))
    except (ValueError, TypeError):
        pagenum = paginator.num_pages
    try:
        page = paginator.page(pagenum)
    except (EmptyPage, InvalidPage):
        page = paginator.page(paginator.num_pages)
    context = {}
    context['is_paginated'] = True
    context['page_obj'] = page
    context['message_list'] = page.object_list
    context['characterid'] = characterid
    context['charactername'] = name
    for message in page.object_list:
        message.read_by_handler = True
        message.save()
    return direct_to_template(request, 'shop/handle-messages.html',
                              extra_context=context)

##################################################################
# Helper classes

class ShopInfo(object):
    def __init__(self):
        self.salespoint_list = SalesOffice.objects.all()

def top_3():
    c = connection.cursor()
    c.execute("""
SELECT SUM((tr.price - (pl.productioncost * pl.safetymargin)) * tr.quantity)
         AS profit,
       SUM(tr.quantity) AS qty,
       tr.typeid,
       pl.typename
FROM industry_transaction tr
     INNER JOIN industry_pricelist pl
       ON tr.typeid = pl.typeid
WHERE tr.transactiontype = 'sell'
  AND tr.timestamp >= NOW() - INTERVAL '28 days'
GROUP BY tr.typeid, pl.typename
ORDER BY profit DESC
LIMIT 5
""")
    result = [ProductList.objects.get(typeid=typeid)
              for (profit, qty, typeid, typename) in c.fetchall()]
    result2 = []
    for pl in result:
        marketprice = pl.marketprice
        if marketprice is None:
            continue
        saving = pl.saving
        if saving is None:
            continue
        if saving / marketprice > 0.1:
            result2.append(pl)
        if len(result2) >= 3:
            break
    return result2

class ShopUser(object):
    def __init__(self):
        self.characterid = None
        self.name = None
        self.corpid = None
        self.corpname = None
        self.allianceid = None
        self.alliancename = ''
        self.standing = 0
        self.lastchecked = None
        self.cart = {}

    @classmethod
    def from_request(cls, request):
        if 'grdshopuser' in request.session:
            shopuser = request.session['grdshopuser']
        else:
            shopuser = cls()
        if (shopuser.characterid is None and
            request.user.is_authenticated() and
            request.user.profile.characterid is not None
            ):
            shopuser.characterid = request.user.profile.characterid
            try:
                shopuser.recheck()
            except:
                shopuser = cls()
        if (shopuser.lastchecked is not None and
            shopuser.lastchecked < (datetime.datetime.utcnow() -
                                    datetime.timedelta(days=1))):
            try:
                shopuser.recheck()
            except:
                pass
        return shopuser

    def save(self, request):
        request.session['grdshopuser'] = self
        request.session.modified = True

    def add(self, typeid, qty):
        self.cart.setdefault(typeid, 0)
        self.cart[typeid] += qty

    def set(self, typeid, qty):
        self.cart[typeid] = qty
        if qty == 0:
            del self.cart[typeid]

    @property
    def cartcount(self):
        return len(self.cart)

    @property
    def ordercount(self):
        if self.characterid is None:
            return 0
        return Order.objects.filter(
            characterid=self.characterid,
            closed=None
            ).count()

    @property
    def discount(self):
        if self.corpname == 'Gradient':
            return 'gradient'
        elif self.standing > 0:
            return 'ally'
        elif self.standing < 0:
            return 'enemy'
        else:
            return None

    @property
    def messagecount(self):
        return Message.objects.filter(characterid=self.characterid,
                                      read_by_customer=False).count()

    @property
    def multiplier(self):
        d = self.discount
        if d == 'gradient':
            return 1.0
        elif d == 'ally':
            return 1.05
        elif d == 'enemy':
            return 5.0
        else:
            return 1.05

    def recheck(self):
        api = apiroot()
        info = api.eve.CharacterInfo(characterID=self.characterid)
        self.name = info.characterName
        self.corpid = info.corporationID
        self.corpname = info.corporation
        self.allianceid = getattr(info, 'allianceID', None)
        self.alliancename = getattr(info, 'alliance', '')

        em = APIKey.objects.get(name='Gradient').corp()
        cl = em.ContactList()
        self.standing = 0
        for contact in cl.allianceContactList:
            if contact.contactID in [self.corpid, self.allianceid]:
                self.standing = contact.standing
                break
        self.lastchecked = datetime.datetime.utcnow()

def add_shop_status(request, status):
    if OrderHandler.objects.filter(user=request.user).exists():
        numopen = Order.objects.filter(closed=None).count()
        nummessages = Message.objects.filter(read_by_handler=False).count()
        if numopen > 0 or nummessages > 0:
            status.append(
                {'text': "%i open order%s" % (numopen,
                                              "s" if numopen != 1
                                              else ""),
                 'url': 'http://gradient.electusmatari.com/shop/handle/'})
            status.append(
                {'text': "%i message%s" % (nummessages,
                                           "s" if nummessages != 1
                                           else ""),
                 'url': "http://gradient.electusmatari.com/shop/handle/messages/"})
