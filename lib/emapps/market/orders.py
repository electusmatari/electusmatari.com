import cgi

import kgi

from emapps.util import eve_time
from emapps.util import require_permission
from emapps.responses import unauthorized

STATES = ["unclaimed", "claimed", "delivered", "done"]

SOURCES = [
    (None, "Electus Matari", "General buy order to be handled by anyone "
     "in the alliance."),
    # (None, "Gradient (Pator)", 'Produces everything Gradient can '
    #  'produce. See <a href="http://kivimaa.fi/ships.html">here</a> for '
    #  'estimated prices.'),
    (None, "Gradient (Dal)", 'Production center for the war effort. '
     'Produces T1 modules and ships up to T1 cruiser size.'),
    # (None, "Gradient Ship Replacement Program (Pator)", 'See <a href="http://kivimaa.fi/gradient/index.php?t=msg&amp;th=409">here</a> '
    #  'for more information.'),
    ('em', "Reimbursement Fund", 'Request refund for lost modules. '
     'Please add a link to the killboard for the loss.'),
    ('admin', "Alliance Market", 'Internal source for sell orders.'),
    ]

@require_permission('em')
def view_own_orders(environ):
    return view_orders(environ, own=True)

@require_permission('em')
def view_orders(environ, own=False):
    """
    View orders - your own, or those assigned to you.
    """
    user = environ['emapps.user']
    form = cgi.FieldStorage()
    if environ["REQUEST_METHOD"] == 'POST':
        orderid = form.getfirst("orderid", None)
        action = form.getfirst("action", None)
        if None in (orderid, action):
            return kgi.redirect_response('http://www.electusmatari.com/market/order/')
        order = sql_get_order(orderid)
        if action == 'cancel':
            if order.customer == user.username:
                sql_drop_order(orderid)
            return kgi.redirect_response('http://www.electusmatari.com/market/order/')
        elif action == 'claim':
            if oder.state == 'unclaimed':
                sql_update_order(orderid, state='claimed',
                                 producer=user.username)
            return kgi.redirect_response('http://www.electusmatari.com/market/order/unclaimed/')
        elif action == 'markdelivered':
            if user.username == order.producer:
                sql_update_order(orderid, state='delivered')
            return kgi.redirect_response('http://www.electusmatari.com/market/order/')
        elif action == 'markdone':
            if user.username == order.producer:
                sql_update_order(orderid, state='done')
            return kgi.redirect_response('http://www.electusmatari.com/market/order/')
        return kgi.redirect_response('http://www.electusmatari.com/market/order/')
    if own:
        title = 'Your Buy Orders'
        orders = sql_get_own_orderlist(user.username)
    else:
        title = 'Buy Requests'
        producer = user.username
        allowed_sources = sql_get_sources(user)
        requested_sources = form.getlist('source')
        sources = [source for source in allowed_sources
                   if len(requested_sources) == 0
                   or source in requested_sources]
        states = form.getlist('state')
        orders = sql_get_orderlist(producer=producer,
                                   sources=sources,
                                   states=states)
    return kgi.template_response('market/order_list.html',
                                 user=user,
                                 current_time=eve_time(),
                                 orders=orders,
                                 title=title,
                                 states=STATES)

def view_order_detail(environ, orderid):
    """
    View a specific order.
    """
    user = environ["emapps.user"]
    order = sql_get_order(orderid)
    if order is None:
        return kgi.template_response('404.html', status='404 Not Found')
    elif not (user.username in [order.customer, order.producer]
              or user.has_permission('producer')):
        return kgi.template_response('403.html', status='403 Forbidden',
                                     reason='This is none of your orders.')
    elif environ["REQUEST_METHOD"] == "POST":
        form = cgi.FieldStorage()
        text = form.getfirst("comment", None)
        if text is not None:
            sql_add_comment(orderid, user.username, text)
        return kgi.redirect_response('http://www.electusmatari.com/market/order/%s/'
                                     % orderid)
    else:
        comments = sql_get_comments(orderid)
        return kgi.template_response('market/order_detail.html',
                                     user=user,
                                     current_time=eve_time(),
                                     order=order,
                                     comments=comments)

@require_permission('producer')
def view_order_edit(environ, orderid):
    """
    Edit a specific order.
    """
    user = environ["emapps.user"]
    order = sql_get_order(orderid)
    if order is None:
        return kgi.redirect_response('http://www.electusmatari.com/market/order/')
    if environ["REQUEST_METHOD"] == "POST":
        form = cgi.FieldStorage()
        customer = form.getfirst('customer')
        source = form.getfirst('source')
        state = form.getfirst('state')
        producer = form.getfirst('producer')
        if producer == '':
            producer = None
        price = form.getfirst('price')
        if price == '':
            price = None
        ordertext = form.getfirst('ordertext')
        if None not in (customer, source, state, ordertext):
            sql_update_order(orderid, customer=customer, source=source,
                             state=state, producer=producer, price=price,
                             ordertext=ordertext)
        return kgi.redirect_response('http://www.electusmatari.com/market/order/%s/'
                                     % orderid)
    return kgi.template_response('market/order_edit.html',
                                 user=user,
                                 order=order,
                                 sources=SOURCES,
                                 states=STATES)

def view_orders_create(environ):
    """
    Form to create a new order.
    """
    user = environ["emapps.user"]
    if not user.is_authenticated():
        return kgi.html_response(
            unauthorized(user, 'You need to log in to the forums.')
            )
    if environ["REQUEST_METHOD"] == "POST":
        form = cgi.FieldStorage()
        ordertext = form.getfirst("ordertext", None)
        source = form.getfirst("source", None)
        comment = form.getfirst("comment", "")
        comment = comment.strip()
        if comment == "":
            comment = None
        if None in (ordertext, source):
            return kgi.redirect_response('http://www.electusmatari.com/market/order/create/')
        sql_create_order(user.username, ordertext, source, comment)
        return kgi.redirect_response('http://www.electusmatari.com/market/order/')
    return kgi.template_response('market/order_create.html',
                                 user=environ["emapps.user"],
                                 sources=SOURCES
                                 )

def sql_create_order(username, ordertext, source, comment=None, price=None,
                     producer=None, state='unclaimed'):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("INSERT INTO market_order_old (ordertext, price, "
              "customer, producer, source, state) "
              "VALUES (%s, %s, %s, %s, %s, %s)",
              (ordertext, price, username, producer, source, state))
    if comment is not None:
        # This is non-portable. PostgreSQL doesn't do c.lastrowid.
        c.execute("INSERT INTO market_comments (order_id, "
                  "author, comment) "
                  "VALUES (%s, %s, %s)",
                  (c.lastrowid, username, comment))

def sql_get_comment(orderid):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("SELECT * FROM market_comments "
              "WHERE order_id = %s "
              "ORDER BY created DESC "
              "LIMIT 1",
              (orderid,))
    if c.rowcount == 1:
        return kgi.fetchbunches(c)[0]
    else:
        return None

def sql_get_own_orderlist(customer):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("SELECT * FROM market_order_old "
              "WHERE state != 'done' "
              "  AND customer = %s "
              "ORDER BY created DESC",
              (customer,))
    orders = kgi.fetchbunches(c)
    for order in orders:
        c = sql_get_comment(order.id)
        if c is not None:
            order['lastcomment'] = c
        else:
            order['lastcomment'] = None
    return orders

def sql_get_orderlist(producer, sources=[], states=[]):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    where = ["state != 'done'"]
    or_where = []
    args = []
    if producer is not None:
        or_where.append("producer = %s")
        args.append(producer)
    if len(sources) > 0:
        or_where.append("(producer is NULL OR producer = '') AND source IN (%s)"
                        % ", ".join(["%s"] * len(sources)))
        args.extend(sources)
    if len(or_where) > 0:
        where.append("(%s)" % (" OR ".join([("(%s)" % x) for x in or_where]),))
    if len(states) > 0:
        where.append("status IN (%s)"
                     % ", ".join(["%s"] * len(states)))
        args.extend(states)
    c.execute("SELECT * FROM market_order_old "
              "WHERE " + " AND ".join(where) + " "
              "ORDER BY source ASC, created DESC",
              args)
    orders = kgi.fetchbunches(c)
    for order in orders:
        c = sql_get_comment(order.id)
        if c is not None:
            order['lastcomment'] = c
        else:
            order['lastcomment'] = None
    return orders

def sql_get_order(orderid):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("SELECT * FROM market_order_old "
              "WHERE id = %s "
              "LIMIT 1",
              (orderid,))
    if c.rowcount == 1:
        return kgi.fetchbunches(c)[0]
    else:
        return None

def sql_get_comments(orderid):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("SELECT * FROM market_comments "
              "WHERE order_id = %s "
              "ORDER BY created ASC",
              (orderid,))
    return kgi.fetchbunches(c)

def sql_add_comment(orderid, author, text):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("INSERT INTO market_comments (order_id, author, comment) "
              "VALUES (%s, %s, %s)",
              (orderid, author, text))

def sql_drop_order(orderid):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("DELETE FROM market_order_old WHERE id = %s",
              (orderid,))

def sql_update_order(orderid, customer=None, source=None, state=None,
                     producer=False, price=False, ordertext=None):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    sets = []
    args = []
    if customer is not None:
        sets.append("customer = %s")
        args.append(customer)
    if source is not None:
        sets.append("source = %s")
        args.append(source)
    if state is not None:
        sets.append("state = %s")
        args.append(state)
    if producer is not False:
        sets.append("producer = %s")
        args.append(producer)
    if price is not False:
        sets.append("price = %s")
        args.append(price)
    if ordertext is not None:
        sets.append("ordertext = %s")
        args.append(ordertext)
    args.append(orderid)
    c.execute("UPDATE market_order_old SET "
              + ", ".join(sets)
              + " WHERE id = %s",
              args)

def sql_get_sources(user):
    # FIXME! Testing purposes.
    return [source for (permission, source, desc) in SOURCES]
