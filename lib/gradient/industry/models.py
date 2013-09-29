import datetime

from django.db import models
from django.contrib.auth.models import User

from gradient.dbutils import get_typename, get_itemname
from gradient.index.models import Index

ORDERTYPE_CHOICES = [('sell', 'Sell Order'),
                     ('buy', 'Buy Order')]

class Account(models.Model):
    accountkey = models.IntegerField()
    name = models.CharField(max_length=128)

class BlueprintOriginal(models.Model):
    typeid = models.BigIntegerField(unique=True)
    typename = models.CharField(max_length=255)
    me = models.IntegerField()
    pe = models.IntegerField()

    class Meta:
        ordering = ["typename"]

class LastUpdate(models.Model):
    name = models.CharField(max_length=32)
    timestamp = models.DateTimeField()

    class Meta:
        ordering = ["name"]

def set_last_update(name, ts):
    try:
        lu = LastUpdate.objects.get(name=name)
    except LastUpdate.DoesNotExist:
        lu = LastUpdate(name=name)
    lu.timestamp = ts
    lu.save()

class Transaction(models.Model):
    transactionid = models.BigIntegerField(unique=True)
    accountkey = models.IntegerField()
    timestamp = models.DateTimeField()
    typeid = models.BigIntegerField()
    quantity = models.IntegerField()
    price = models.FloatField()
    clientid = models.BigIntegerField()
    characterid = models.BigIntegerField()
    stationid = models.BigIntegerField()
    transactiontype = models.CharField(max_length=5)
    journalid = models.BigIntegerField()

    class Meta:
        ordering = ["-timestamp"]

    @property
    def accountname(self):
        try:
            return Account.objects.get(accountkey=self.accountkey).name
        except Account.DoesNotExist:
            return self.accountkey

    @property
    def typename(self):
        return get_typename(self.typeid)

    @property
    def price_total(self):
        return self.price * self.quantity

    @property
    def clientname(self):
        return self.clientid

    @property
    def charactername(self):
        return self.characterid

    @property
    def stationname(self):
        return get_itemname(self.stationid)

class TransactionInfo(models.Model):
    transaction = models.OneToOneField(Transaction, related_name="info")
    account = models.ForeignKey(Account)
    typename = models.CharField(max_length=128)
    cost = models.FloatField()
    safetymargin = models.FloatField(default=1.0)
    stationname = models.CharField(max_length=128)
    charactername = models.CharField(max_length=128)
    clientname = models.CharField(max_length=128, null=True)
    clientstanding = models.IntegerField(null=True)
    clientcorp = models.CharField(max_length=128)
    clientcorpid = models.BigIntegerField()
    clientcorpstanding = models.IntegerField(null=True)
    clientalliance = models.CharField(max_length=128, blank=True, default='')
    clientallianceid = models.BigIntegerField(null=True, default=None)
    clientalliancestanding = models.IntegerField(null=True, default=None)

    @property
    def standing(self):
        if self.clientalliancestanding is not None:
            return self.clientalliancestanding
        if self.clientcorpstanding is not None:
            return self.clientcorpstanding
        if self.clientstanding is not None:
            return self.clientstanding

    @property
    def profit(self):
        if self.transaction.transactiontype == 'sell':
            per_item = (self.transaction.price -
                        (self.cost * self.safetymargin))
        else:
            per_item = ((self.cost * self.safetymargin) -
                        self.transaction.price)
        return self.transaction.quantity * per_item


class Journal(models.Model):
    journalid = models.BigIntegerField(unique=True)
    accountkey = models.IntegerField()
    timestamp = models.DateTimeField()
    reftypeid = models.IntegerField()
    amount = models.FloatField()
    ownerid1 = models.BigIntegerField()
    ownerid2 = models.BigIntegerField()
    argname1 = models.CharField(max_length=255)
    argid1 = models.BigIntegerField()
    reason = models.CharField(max_length=255)

    class Meta:
        ordering = ["timestamp"]

class PriceList(models.Model):
    typename = models.CharField(max_length=255)
    typeid = models.BigIntegerField(unique=True)
    productioncost = models.FloatField()
    safetymargin = models.FloatField()

    class Meta:
        ordering = ["typename"]

class WantedMarketOrder(models.Model):
    characterid = models.BigIntegerField(null=True)
    charactername = models.CharField(max_length=255, blank=True, null=True)
    stationid = models.BigIntegerField()
    stationname = models.CharField(max_length=255, blank=True, null=True)
    typeid = models.BigIntegerField()
    typename = models.CharField(max_length=255, blank=True, null=True)
    forcorp = models.BooleanField(
        verbose_name="For Corp",
        help_text="Global for the corp, as opposed to only for you")
    ordertype = models.CharField(max_length=5, choices=ORDERTYPE_CHOICES)
    quantity = models.IntegerField()
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ['stationname', 'typename']
        unique_together = [('characterid', 'stationid', 'typeid')]

class MarketOrder(models.Model):
    characterid = models.BigIntegerField()
    stationid = models.BigIntegerField()
    typeid = models.BigIntegerField()
    ordertype = models.CharField(max_length=5)
    expires = models.DateTimeField()
    volremaining = models.IntegerField()
    price = models.FloatField()
    productioncost = models.FloatField()
    salesperday = models.FloatField()
    competitionprice = models.FloatField(null=True)
    trend = models.FloatField()

    @property
    def expiredays(self):
        now = datetime.datetime.utcnow()
        return (self.expires - now).days

    @property
    def profitmargin(self):
        if self.price == 0:
            return 0.0
        if self.ordertype == 'sell':
            return 1 - (self.productioncost / self.price)
        else:
            return (self.productioncost - self.price) / self.price

    @property
    def profitperitem(self):
        if self.ordertype == 'sell':
            return self.price - self.productioncost
        else:
            return self.productioncost - self.price

    @property
    def daysremaining(self):
        if self.salesperday == 0:
            return None
        else:
            return int((self.volremaining / float(self.salesperday)) + 0.5)

    @property
    def profitperday(self):
        return self.profitperitem * self.salesperday

    @property
    def suggestedprice(self):
        if self.ordertype == 'sell':
            if self.competitionprice is not None:
                return max((self.competitionprice - 0.01),
                           self.productioncost * 1.1)
            elif self.price < self.productioncost * 1.1:
                return self.productioncost * 1.1
            else:
                return None
        else:
            if self.competitionprice is not None:
                newprice = min((self.competitionprice + 0.01),
                               self.productioncost * 0.9)
            elif self.price > self.productioncost * 0.9:
                return self.productioncost * 0.9
            else:
                return None

class PublicMarketOrder(models.Model):
    last_seen = models.DateTimeField()
    ordertype = models.CharField(max_length=5, choices=ORDERTYPE_CHOICES)
    regionid = models.BigIntegerField()
    systemid = models.BigIntegerField()
    stationid = models.BigIntegerField()
    range = models.IntegerField()
    typeid = models.BigIntegerField()
    volremain = models.IntegerField()
    price = models.FloatField()

class MarketPrice(models.Model):
    last_seen = models.DateTimeField()
    typeid = models.BigIntegerField()
    price = models.FloatField()

class StockLevel(models.Model):
    stationname = models.CharField(max_length=255)
    stationid = models.BigIntegerField()
    typename = models.CharField(max_length=255)
    typeid = models.BigIntegerField()
    low = models.IntegerField()
    high = models.IntegerField()
    comment = models.TextField(blank=True)
    watcher = models.ManyToManyField(User)

    @property
    def current(self):
        try:
            return self.stock.current
        except Stock.DoesNotExist:
            return 0

    @property
    def is_low(self):
        return self.current < self.low

    @property
    def missing(self):
        return max(0, self.high - self.current)

    @property
    def index(self):
        try:
            return Index.objects.filter(typeid=self.typeid)[0:1].get().republic
        except Index.DoesNotExist:
            return None

    class Meta:
        ordering = ["typename"]
        unique_together = [('typeid', 'stationid')]

class Stock(models.Model):
    typename = models.CharField(max_length=255)
    typeid = models.BigIntegerField()
    stationid = models.BigIntegerField()
    current = models.IntegerField()
    level = models.OneToOneField(StockLevel, null=True)
    price = models.ForeignKey(PriceList, null=True)

    class Meta:
        ordering = ["typename"]
        unique_together = [('typeid', 'stationid')]
