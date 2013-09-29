from django.contrib.auth.models import User
from django.db import models

class AuthToken(models.Model):
    user = models.OneToOneField(User, related_name="+")
    tokenstring = models.CharField(max_length=64,
                                   db_index=True, unique=True)
    numuploads = models.IntegerField(default=0)
    numbytes = models.BigIntegerField(default=0)

class Upload(models.Model):
    user = models.ForeignKey(User)
    uploadtimestamp = models.DateTimeField(auto_now_add=True)
    cachetimestamp = models.DateTimeField()
    method = models.CharField(max_length=128)

class CorpFactionHistory(models.Model):
    corporationid = models.BigIntegerField()
    factionid = models.BigIntegerField()
    starttimestamp = models.DateTimeField()
    endtimestamp = models.DateTimeField(null=True)
    uploads = models.ManyToManyField(Upload)

class MarketHistoryLastUpload(models.Model):
    cachetimestamp = models.DateTimeField()
    regionid = models.BigIntegerField(db_index=True)
    typeid = models.BigIntegerField(db_index=True)

    class Meta:
        unique_together = [('typeid', 'regionid')]

class MarketHistory(models.Model):
    upload = models.ForeignKey(Upload)
    cachetimestamp = models.DateTimeField()

    regionid = models.BigIntegerField(db_index=True)
    typeid = models.BigIntegerField(db_index=True)
    historydate = models.DateField(db_index=True)
    lowprice = models.FloatField()
    highprice = models.FloatField()
    avgprice = models.FloatField()
    volume = models.BigIntegerField()
    orders = models.IntegerField()

    class Meta:
        unique_together = [('regionid', 'typeid', 'historydate')]

class MarketOrderLastUpload(models.Model):
    cachetimestamp = models.DateTimeField()
    regionid = models.BigIntegerField(db_index=True)
    typeid = models.BigIntegerField(db_index=True)

class MarketOrder(models.Model):
    upload = models.ForeignKey(Upload)
    cachetimestamp = models.DateTimeField()

    orderid = models.BigIntegerField()
    stationid = models.BigIntegerField(db_index=True)
    solarsystemid = models.BigIntegerField(db_index=True)
    regionid = models.BigIntegerField(db_index=True)

    volentered = models.BigIntegerField()
    volremaining = models.BigIntegerField()
    minvolume = models.BigIntegerField()

    typeid = models.BigIntegerField(db_index=True)
    range = models.IntegerField()
    duration = models.IntegerField()
    price = models.FloatField()
    bid = models.BooleanField()
    issuedate = models.DateTimeField()

class FacWarSystem(models.Model):
    upload = models.ForeignKey(Upload)
    cachetimestamp = models.DateTimeField()
    
    solarsystemid = models.BigIntegerField()
    solarsystemname = models.CharField(max_length=128)
    occupyingfactionid = models.BigIntegerField()
    occupyingfactionname = models.CharField(max_length=128)
    owningfactionid = models.BigIntegerField()
    owningfactionname = models.CharField(max_length=128)
    victorypoints = models.IntegerField()
    threshold = models.IntegerField()

    def percentage(self):
        return "%.1f%%" % ((self.victorypoints * 100.0) / self.threshold)

class FacWarSystemHistory(models.Model):
    upload = models.ForeignKey(Upload)
    cachetimestamp = models.DateTimeField()
    
    solarsystemid = models.BigIntegerField()
    occupyingfactionid = models.BigIntegerField()
    victorypoints = models.IntegerField()
    threshold = models.IntegerField()

