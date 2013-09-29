# Buy and sell order

import cgi
import datetime

import kgi
from emapps.util import require_permission, humane
from contracts import sql_create_contract, sql_add_comment

def view_order_sell(environ):
    return view_order(environ, type="sell")

def view_order_buy(environ):
    return view_order(environ, type="buy")

@require_permission('em')
def view_order(environ, type):
    form = cgi.FieldStorage()
    user = environ["emapps.user"]
    if environ["REQUEST_METHOD"] == "POST":
        cancel = [field[6:] for field in form.keys()
                  if field.startswith("cancel")]
        if len(cancel) > 0:
            for orderid in cancel:
                sql_cancel_order(user.username, orderid)
            return kgi.redirect_response('http://www.electusmatari.com/market2/')
        orders = {}
        for field in form.keys():
            if field.startswith("order"):
                try:
                    orderid = int(field[5:])
                    amount = int(form.getfirst(field))
                except Exception, e:
                    return kgi.template_response('market2/error.html',
                                                 user=user,
                                                 error=str(e))
                if orderid not in orders:
                    orders[orderid] = 0
                orders[orderid] += amount
        if len(orders) == 0:
            return kgi.template_response('market2/error.html',
                                         user=user,
                                         error="Please enter at least one item to buy.")
        else:
            contractid = sql_save_order(user.username, orders, type)
            if contractid is None:
                return kgi.redirect_response('http://www.electusmatari.com/market2/contracts/')
            else:
                return kgi.redirect_response('http://www.electusmatari.com/market2/contracts/%i/' % contractid)
    orders = get_orders(type, form.getfirst("sort", None))
    return kgi.template_response('market2/order.html',
                                 user=user,
                                 type=type,
                                 orders=orders)

@require_permission('em')
def view_order_create(environ):
    user = environ["emapps.user"]
    if environ["REQUEST_METHOD"] == "POST":
        form = cgi.FieldStorage()
        item = form.getfirst("item", '')
        amount = form.getfirst("amount", None)
        price = form.getfirst("price", None)
        expires = form.getfirst("expires", None)
        comment = form.getfirst("comment", '')
        type = form.getfirst("type", "sell")
        if type not in ('sell', 'buy'):
            type = 'sell'
        try:
            amount = int(amount)
            price = float(price)
            expires = int(expires)
        except Exception, e:
            return kgi.template_response('market2/error.html',
                                         user=user,
                                         error="The fields amount, price and expires are required.")
        if amount <= 0:
            return kgi.template_response('market2/error.html',
                                         user=user,
                                         error='Amount should be positive.')
        sql_create_order(environ["emapps.user"].username,
                         type,
                         item,
                         amount,
                         price,
                         comment,
                         expires)
        return kgi.redirect_response('http://www.electusmatari.com/market2/create/')
    return kgi.template_response('market2/order_create.html',
                                 user=environ["emapps.user"])

def view_rss(environ):
    pass

def get_orders(ordertype, sortby=None):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    query = "SELECT * FROM market_order "
    if ordertype == 'sell':
        query += " WHERE type = 'sell' "
    else:
        query += " WHERE type = 'buy' "
    if sortby == 'age':
        query += "ORDER BY created DESC"
    else:
        query += "ORDER BY item ASC"
    c.execute(query)
    now = datetime.datetime.now()
    bunches = kgi.fetchbunches(c)
    for b in bunches:
        b.age = (now - b.created).days
    return bunches

def sql_create_order(username, type, item, amount, price, comment, expires):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    expires = datetime.datetime.utcnow() + datetime.timedelta(days=expires)
    c.execute("INSERT INTO market_order (expires, type, amount, item, "
              "                          price, owner, comment) "
              "VALUES (%s, %s, %s, %s, %s, %s, %s)",
              (expires, type, amount, item, price, username, comment))


def sql_cancel_order(username, orderid):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("DELETE FROM market_order "
              "WHERE id = %s AND owner = %s",
              (orderid, username))

def sql_save_order(username, orders, type):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    ordertexts = {}
    comments = {}
    totals = {}
    args = orders.keys()
    args.append(type)
    contractids = []
    c.execute("SELECT * FROM market_order "
              "WHERE id IN (%s) "
              "  AND type = %%s "
              "ORDER BY item ASC" % ", ".join(["%s"] * len(orders)),
              args)
    bunches = kgi.fetchbunches(c)
    for b in bunches:
        amount = orders[b.id]
        if b.amount <= 0 or b.amount < amount:
            continue
        b.amount -= amount
        if b.owner not in ordertexts:
            ordertexts[b.owner] = ""
        if b.owner not in comments:
            comments[b.owner] = ""
        if b.owner not in totals:
            totals[b.owner] = 0
        ordertexts[b.owner] += ("%ix %s\n" % (amount, b.item))
        comments[b.owner] += ("%15s %s x %s (%s p.u., %s)\n"
                              % (humane(amount * b.price),
                                 b.item,
                                 humane(amount),
                                 humane(b.price),
                                 b.comment))
        totals[b.owner] += amount * b.price
    for (owner, comment) in comments.items():
        comments[owner] += "---------------\n"
        comments[owner] += "%15s sum" % humane(totals[owner])
    for owner in ordertexts.keys():
        if type == 'sell':
            creator = username
            handler = owner
        else:
            creator = owner
            handler = username
        contractids.append(sql_create_contract(creator=creator,
                                               contracttext=ordertexts[owner],
                                               handler=handler,
                                               state="in progress"))
        sql_add_comment(contractids[-1], creator, comments[owner])
    for b in bunches:
        if b.amount == 0:
            c.execute("DELETE FROM market_order WHERE id = %s",
                      (b.id,))
        else:
            c.execute("UPDATE market_order SET amount = %s WHERE id = %s",
                      (b.amount, b.id))
    if len(contractids) == 1:
        return contractids[0]
    else:
        return None
