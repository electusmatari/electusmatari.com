import datetime

from emtools.ccpeve import eveapi
from django.db import models

from ccpmodels import *
from ccputils import InvItem

class APIKey(models.Model):
    name = models.CharField(max_length=255)
    keyid = models.CharField(max_length=32, null=True, blank=True)
    vcode = models.CharField(max_length=128, null=True, blank=True)
    userid = models.CharField(max_length=32, null=True, blank=True)
    apikey = models.CharField(max_length=128, null=True, blank=True)
    characterid = models.CharField(max_length=32)
    active = models.BooleanField()
    message = models.TextField(max_length=255, blank=True)
    last_attempt = models.DateTimeField()

    def __unicode__(self):
        return "API Key %s" % self.name

    def root(self):
        api = apiroot()
        if self.keyid:
            return api.auth(keyID=self.keyid, vCode=self.vcode)
        else:
            return api.auth(userID=self.userid, apiKey=self.apikey)

    def char(self):
        return self.root().character(characterID=self.characterid)

    def corp(self):
        return self.root().corporation(characterID=self.characterid)

class Cache(models.Model):
    cacheduntil = models.DateTimeField()
    host = models.CharField(max_length=255)
    path = models.CharField(max_length=255)
    params = models.TextField()
    doc = models.TextField()

    class Meta:
        unique_together = [("host", "path", "params")]

def apiroot():
    return eveapi.EVEAPIConnection(cacheHandler=DBCache())

class DBCache(object):
    def retrieve(self, host, path, params):
        try:
            cached = Cache.objects.exclude(
                cacheduntil__lt=datetime.datetime.utcnow()
                ).get(host=host, path=path, params=repr(params))
        except Cache.DoesNotExist:
            return None
        return cached.doc.encode("utf-8")

    def store(self, host, path, params, doc, obj):
        # Ugly hack for bug #106748
        if hasattr(obj, 'cachedUntil'):
            cacheduntil = datetime.datetime.utcfromtimestamp(obj.cachedUntil)
        else:
            cacheduntil = datetime.datetime.utcfromtimestamp(obj.result.cachedUntil)
        obj, created = Cache.objects.get_or_create(
            host=host,
            path=path,
            params=repr(params),
            defaults={'doc': doc,
                      'cacheduntil': cacheduntil})
        if not created:
            obj.doc = doc
            obj.cacheduntil = cacheduntil
            obj.save()

class Division(models.Model):
    apitimestamp = models.DateTimeField()
    ownerid = models.BigIntegerField()

    accountKey = models.IntegerField()
    hangarname = models.CharField(max_length=255)
    walletname = models.CharField(max_length=255)

    class Meta:
        unique_together = (('apitimestamp', 'ownerid', 'accountKey'),)
        ordering = ['ownerid', 'accountKey']
