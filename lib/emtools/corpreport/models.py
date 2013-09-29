from django.db import models

from emtools.ccpeve.models import Division, Type

PRODUCTION_CATEGORIES = [
    'Fixed Assets',
    'Infrastructure',
    'Minerals',
    'Moon Reactions',
    'Pharmaceuticals',
    'Planetary Industry',
    'Starbase Fuel',
    'T1 Ships',
    'T1 Capitals',
    'T1 Modules',
    'T1 Rigs',
    'Meta Modules',
    'T2 Production',
    'T2 Capitals',
    'T2 Rigs',
    'T3 Production',
    'Unknown',
    ]

class DivisionConfig(models.Model):
    division = models.OneToOneField(Division)
    usewallet = models.BooleanField()
    usehangar = models.BooleanField()

class ReportCategory(models.Model):
    type = models.OneToOneField(Type)
    category = models.CharField(max_length=255, null=True, blank=True,
                                choices=[(cat, cat)
                                         for cat in PRODUCTION_CATEGORIES])

    class Meta:
        ordering = ('type__typeName',)

