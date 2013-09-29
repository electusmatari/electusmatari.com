import urllib
from xml.etree import ElementTree

QUICKLOOK_URL = 'http://api.eve-central.com/api/quicklook'

def quicklook(typeid, sethours=None, regionlimit=None, usesystem=None,
              setminQ=None):
    args = [('typeid', typeid)]
    if sethours is not None:
        args.append(('sethours', sethours))
    if regionlimit is not None:
        args.extend(('regionlimit', region) for region in regionlimit)
    if usesystem is not None:
        args.append(('usesystem', usesystem))
    if setminQ is not None:
        args.append(('setminQ', setminQ))
    url = urllib.urlopen(QUICKLOOK_URL + '?' + urllib.urlencode(args))
    tree = ElementTree.parse(url)
    for order in tree.findall("quicklook/sell_orders/order"):
        yield {'regionid': int(order.find('region').text),
               'stationid': int(order.find('station').text),
               'price': float(order.find('price').text),
               'quantity': int(order.find('vol_remain').text),
               'checked': order.find("reported_time").text}
