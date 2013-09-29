from functools import wraps

from emtools.ccpeve.models import LastUpdated
from emtools.ccpeve.models import Asset, MarketOrder
from emtools.ccpeve.models import Type, Station

def memoize(f):
    cache = {}
    @wraps(f)
    def wrapper(*args):
        if args in cache:
            return cache[args]
        rv = f(*args)
        cache[args] = rv
        return rv
    return wrapper

def get_locations(ownerid):
    officestations = get_officestations(ownerid)
    sellstations, buystations = get_marketstations(ownerid)
    
    sales_center = officestations & sellstations
    logistics_center = (officestations & buystations) - sales_center
    offices = officestations - sales_center - logistics_center
    sales_points = sellstations - officestations
    purchase_points = buystations - officestations

    sales_center = Station.objects.in_bulk(sales_center).values()
    logistics_center = Station.objects.in_bulk(logistics_center).values()
    offices = Station.objects.in_bulk(offices).values()
    sales_points = Station.objects.in_bulk(sales_points).values()
    purchase_points = Station.objects.in_bulk(purchase_points).values()

    return (sales_center, logistics_center, offices,
            sales_points, purchase_points)

def get_officestations(ownerid):
    office = Type.objects.get(typeName='Office')
    ts = LastUpdated.objects.get(ownerid=ownerid,
                                 methodname='/corp/AssetList'
                                 ).apitimestamp
    qs = Asset.objects.filter(ownerid=ownerid,
                              typeID=office.typeID,
                              apitimestamp=ts)
    return set(row.location.stationID
               for row in qs)

def get_marketstations(ownerid):
    sell = set()
    buy = set()
    ts = LastUpdated.objects.get(ownerid=ownerid,
                                 methodname='/corp/MarketOrders'
                                 ).apitimestamp
    qs = MarketOrder.objects.filter(ownerid=ownerid,
                                    apitimestamp=ts)
    for order in qs:
        if order.bid:
            buy.add(order.stationID)
        else:
            sell.add(order.stationID)
    return sell, buy

class IgnoreEntry(Exception):
    pass
