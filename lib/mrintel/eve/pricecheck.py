import urllib
from xml.etree import ElementTree

from mrintel.eve import evecentral
from mrintel.eve.dbutils import DBConnection

REGION_HEIMATAR = 10000030
REGION_METROPOLIS = 10000042
REGION_MOLDENHEATH = 10000028
REGION_THEFORGE = 10000002


def format_reply(price, query):
    # Not found
    if 'source' not in price:
        typenames = price['typenames']
        if len(typenames) == 0:
            return ('I am sorry, but I could not find a type named like {0}. '
                    'Is there a typo?'.format(repr(query)))
        elif len(typenames) < 5:
            return ("I'm not sure what you mean, pick one of these? {0}"
                    .format(", ".join(repr(tn) for tn in typenames)))
        else:
            return ("I found {0:,} type names matching {1}, could you be "
                    "a bit more specific?"
                    .format(len(typenames), query))
    # NPC sell order
    if price['source'] == 'npc':
        if len(price['corporations']) > 5:
            seller = ("{0:,} non-capsuleer corporations"
                      .format(len(price['corporations'])))
        else:
            seller = ", ".join(sorted(price['corporations']))
        return ("{typename} is sold by {seller} on the open market "
                "for {price:,.2f} ISK."
                .format(seller=seller, **price))
    # Contracts
    if price['source'] == 'contracts':
        if price['price'] is None:
            return ("{typename} should be sold via contracts, but no prices "
                    "have been reported.".format(**price))
        else:
            return ("Capsuleers report to have seen {typename} sold via "
                    "contracts for {price:,.2f} ISK.".format(**price))
    # Market
    if price['source'] == 'market':
        if price['price'] is None:
            return ("{typename} should be available on the open market, "
                    "but no prices have been reported.".format(**price))
        else:
            return ("{typename} is sold for {price:,.2f} ISK "
                    "(for {quantity:,} units) in {system}, {region}."
                    .format(**price))


def pricecheck(typename):
    conn = DBConnection()
    typename, typeid = conn.find_type(typename)
    if typeid is None:
        return {'typenames': typename}
    corplist = conn.sold_by_npccorps(typeid)
    if len(corplist) > 0:
        return {'source': 'npc',
                'typename': typename,
                'corporations': corplist,
                'price': conn.baseprice(typeid) * 0.9}
    if conn.marketgroup(typeid) is None:
        return {'source': 'contracts',
                'typename': typename,
                'price': faction_pricecheck(typeid)}
    marketorders = list(evecentral.quicklook(typeid=typeid,
                                             sethours=7 * 24,
                                             regionlimit=[REGION_HEIMATAR,
                                                          REGION_METROPOLIS,
                                                          REGION_MOLDENHEATH,
                                                          REGION_THEFORGE]))
    marketorders.extend(conn.pricecheck(typeid=typeid,
                                        sethours=7 * 24,
                                        regionlimit=[REGION_HEIMATAR,
                                                     REGION_METROPOLIS,
                                                     REGION_MOLDENHEATH,
                                                     REGION_THEFORGE]))
    if len(marketorders) == 0:
        return {'source': 'market', 'price': None}
    marketorders.sort(key=lambda order: order['price'])
    order = marketorders[0]
    if 'systemname' not in order:
        if 'stationid' in order:
            order['systemname'] = conn.stationid2systemname(order['stationid'])
    if 'regionname' not in order:
        order['regionname'] = conn.itemname(order['regionid'])
    return {'source': 'market',
            'typename': typename,
            'price': order['price'],
            'quantity': order['quantity'],
            'system': order['systemname'],
            'region': order['regionname'],
            'checked': order['checked']}

def faction_pricecheck(typeid):
    u = urllib.urlopen("http://prices.c0rporation.com/faction.xml")
    tree = ElementTree.fromstring(u.read())
    for row in tree.findall("result/rowset/row"):
        if row.attrib['typeID'] == str(typeid):
            return float(row.attrib['avg'])
    return None
