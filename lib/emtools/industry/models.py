from django.db import models

from emtools.ccpeve.models import Type

class BlueprintOriginal(models.Model):
    ownerid = models.BigIntegerField()
    blueprint = models.ForeignKey(Type)
    me = models.IntegerField()
