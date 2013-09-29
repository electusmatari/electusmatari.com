from django.db import models
from django.contrib.auth.models import User

class TZConfig(models.Model):
    user = models.ForeignKey(User)
    timezone = models.CharField(max_length=128)
    public = models.BooleanField()
