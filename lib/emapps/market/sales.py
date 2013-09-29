import cgi
import datetime

import kgi

from emapps.util import require_permission, humane

from orders import sql_create_order

def view_sales(environ):
    """
    Display all active sell orders.
    """
    form = cgi.FieldStorage()
    user = environ["emapps.user"]
    if user.has_permission('em'):
        if environ["REQUEST_METHOD"] == "POST":
            cancel = [field[6:] for field in form.keys()
                      if field.startswith("cancel")]
            if len(cancel) > 0:
                for orderid in cancel:
                    sql_cancel_order(user.username, orderid)
                return kgi.redirect_response('http://www.electusmatari.com/market/')
            orders = {}
            for field in form.keys():
                if field.startswith("order"):
                    try:
                        orderid = int(field[5:])
                        amount = int(form.getfirst(field))
                    except:
                        return kgi.redirect_response('http://www.electusmatari.com/market/')
                    if orderid not in orders:
                        orders[orderid] = 0
                    orders[orderid] += amount
            if len(orders) == 0:
                return kgi.template_response('market/error.html',
                                             user=user,
                                             error="Please enter at least one item to buy.")
            else:
                sql_save_order(user.username, orders)
                return kgi.redirect_response('http://www.electusmatari.com/market/')
        sales = get_sales(form.getfirst("sort", None))
    else:
        sales = []
    return kgi.template_response('market/sales.html',
                                 user=user,
                                 sales=sales)

def view_sales_rss(environ):
    """
    RSS feed of all active sell orders
    """
    import PyRSS2Gen as RSS2
    rss = RSS2.RSS2(
        title='Electus Market',
        link='http://www.electusmatari.com/market/',
        description='Alliance offers',
        lastBuildDate=datetime.datetime.now(),
        items = [
            RSS2.RSSItem(
                title=sale.item,
                link="http://www.electusmatari.com/market/",
                description="%s ISK<br />%s" % (humane(sale.price),
                                                sale.comment),
                guid=RSS2.Guid(str(sale.id)),
                pubDate=sale.created)
            for sale
            in get_sales(sortby="age")]
        )
    return kgi.html_response(rss.to_xml(),
                             header=[('Content-Type', 'application/rss+xml')])
    

@require_permission('em')
def view_sales_create(environ):
    """
    Form to create sell orders.
    """
    if environ["REQUEST_METHOD"] == "POST":
        form = cgi.FieldStorage()
        item = form.getfirst("item", '')
        amount = form.getfirst("amount", None)
        price = form.getfirst("price", None)
        comment = form.getfirst("comment", '')
        try:
            amount = int(amount)
            price = float(price)
        except:
            return kgi.redirect_response('http://www.electusmatari.com/market/create/')
        sql_create_sellorder(environ["emapps.user"].username,
                             item,
                             amount,
                             price,
                             comment)
        return kgi.redirect_response('http://www.electusmatari.com/market/create/')
    return kgi.template_response('market/sales_create.html',
                                 user=environ["emapps.user"])

def get_sales(sortby=None):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    query = "SELECT * FROM market_sale "
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

def sql_create_sellorder(owner, item, amount, price, comment):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("INSERT INTO market_sale (amount, item, price, owner, comment) "
              "VALUES (%s, %s, %s, %s, %s)",
              (amount, item, price, owner, comment))

def sql_save_order(username, orders):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    ordertexts = {}
    comments = {}
    totals = {}
    c.execute("SELECT * FROM market_sale "
              "WHERE id IN (%s) "
              "ORDER BY item ASC" % ", ".join(["%s"] * len(orders)),
              orders.keys())
    bunches = kgi.fetchbunches(c)
    for b in bunches:
        amount = orders[b.id]
        if b.amount == 0 or b.amount < amount:
            return
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
        sql_create_order(username, ordertexts[owner], "Alliance Market",
                         comments[owner], price=totals[owner],
                         producer=owner, state="claimed")
    for b in bunches:
        if b.amount == 0:
            c.execute("DELETE FROM market_sale WHERE id = %s",
                      (b.id,))
        else:
            c.execute("UPDATE market_sale SET amount = %s WHERE id = %s",
                      (b.amount, b.id))

def sql_cancel_order(username, orderid):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("DELETE FROM market_sale "
              "WHERE id = %s AND owner = %s",
              (orderid, username))
