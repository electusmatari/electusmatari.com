from django.db import models, connection
from django.contrib.auth.models import User
from gradient.industry.models import PriceList, MarketPrice

class ProductList(PriceList):
    def shopdescription(self):
        return self.description.replace('<font color="yellow">',
                                        '<font color="#FF7F00">')

    class Meta:
        proxy = True

    @property
    def grdprice(self):
        return (self.productioncost *
                self.safetymargin *
                getattr(self, 'multiplier', 1.0))

    @property
    def marketprice(self):
        try:
            return MarketPrice.objects.get(typeid=self.typeid).price
        except MarketPrice.DoesNotExist:
            return None

    @property
    def saving(self):
        mp = self.marketprice
        if mp is None:
            return None
        return self.marketprice - self.grdprice

    @property
    def saving_percentage(self):
        return "%.1f" % ((self.saving / self.marketprice) * 100)

    @property
    def description(self):
        c = connection.cursor()
        c.execute("select description from ccp.invtypes where typeid = %s",
                  (self.typeid,))
        return c.fetchone()[0]

class SalesOffice(models.Model):
    name = models.CharField(max_length=255)
    stationid = models.BigIntegerField()
    stationname = models.CharField(max_length=255)
    description = models.TextField()
    multiplier = models.FloatField(default=1.0)

    class Meta:
        ordering = ['id']

class Order(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    # Customer
    characterid = models.BigIntegerField()
    name = models.CharField(max_length=255)
    corpid = models.BigIntegerField()
    corpname = models.CharField(max_length=255)
    allianceid = models.BigIntegerField(null=True)
    alliancename = models.CharField(max_length=255, blank=True)
    standing = models.FloatField()
    discount = models.CharField(max_length=32, blank=True)
    multiplier = models.FloatField()
    lastchecked = models.DateTimeField()
    # Product
    typeid = models.BigIntegerField()
    typename = models.CharField(max_length=255)
    quantity = models.IntegerField()
    price = models.FloatField()
    # Location
    office = models.ForeignKey(SalesOffice)
    # Order
    handler = models.ForeignKey(User, null=True)
    closed = models.DateTimeField(null=True)
    cancelled = models.BooleanField()
    
    @property
    def price_pu(self):
        return self.price * self.multiplier * self.office.multiplier

    @property
    def price_total(self):
        return self.price_pu * self.quantity

    def standing_string(self):
        if self.corpname == 'Gradient':
            return "Gradient"
        elif self.alliancename == 'Electus Matari':
            return "+10"
        elif self.standing == 0:
            return "neutral"
        else:
            return "%+i" % self.standing


    class Meta:
        ordering = ['name', 'office__id', 'typename']

class Message(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    # Customer
    characterid = models.BigIntegerField()
    name = models.CharField(max_length=255)
    read_by_customer = models.BooleanField()
    read_by_handler = models.BooleanField()
    # Handler, if it was sent by the shop
    handler = models.ForeignKey(User, null=True)
    
    text = models.TextField()

    @property
    def authorname(self):
        if self.handler is not None:
            return self.handler.profile.name
        else:
            return self.name

    @property
    def authorid(self):
        if self.handler is not None:
            return self.handler.profile.characterid
        else:
            return self.characterid

    @property
    def recipientname(self):
        if self.handler is not None:
            return self.name
        else:
            return None

    @property
    def recipientid(self):
        if self.handler is not None:
            return self.characterid
        else:
            return None

    class Meta:
        ordering = ['created']

# This is a somewhat silly way of extending the User model by a
# boolean value.
class OrderHandler(models.Model):
    user = models.OneToOneField(User, primary_key=True)
