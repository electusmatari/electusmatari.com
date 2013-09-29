from django.db import models

class Index(models.Model):
    timestamp = models.DateTimeField(auto_now=True)
    typeid = models.BigIntegerField()
    typename = models.CharField(max_length=128)
    category = models.CharField(max_length=128)
    refineable = models.BooleanField()
    ordering = models.IntegerField()
    republic = models.FloatField()
    republicvolume = models.BigIntegerField()
    republicchange = models.FloatField()
    heimatar = models.FloatField()
    heimatarvolume = models.BigIntegerField()
    heimatarchange = models.FloatField()
    heimatarage = models.IntegerField()
    metropolis = models.FloatField()
    metropolisvolume = models.BigIntegerField()
    metropolischange = models.FloatField()
    metropolisage = models.IntegerField()
    moldenheath = models.FloatField()
    moldenheathvolume = models.BigIntegerField()
    moldenheathchange = models.FloatField()
    moldenheathage = models.IntegerField()
    jita = models.FloatField()
    jitavolume = models.BigIntegerField()
    jitachange = models.FloatField()
    jitaage = models.IntegerField()

    class Meta:
        ordering = ['ordering']

class IndexHistory(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    typeid = models.BigIntegerField()
    republic = models.FloatField()
    republicvolume = models.BigIntegerField()
    republicchange = models.FloatField()
    heimatar = models.FloatField()
    heimatarvolume = models.BigIntegerField()
    heimatarchange = models.FloatField()
    heimatarage = models.IntegerField()
    metropolis = models.FloatField()
    metropolisvolume = models.BigIntegerField()
    metropolischange = models.FloatField()
    metropolisage = models.IntegerField()
    moldenheath = models.FloatField()
    moldenheathvolume = models.BigIntegerField()
    moldenheathchange = models.FloatField()
    moldenheathage = models.IntegerField()
    jita = models.FloatField()
    jitavolume = models.BigIntegerField()
    jitachange = models.FloatField()
    jitaage = models.IntegerField()

    class Meta:
        ordering = ['timestamp', 'typeid']
