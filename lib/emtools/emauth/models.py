from django.db import models

from django.contrib.auth.models import User

from emtools import utils

class Profile(models.Model):
    user = models.OneToOneField(User, primary_key=True)
    mybb_uid = models.IntegerField(null=True)
    mybb_username = models.CharField(max_length=120, null=True)
    usertitle = models.CharField(max_length=120,
                                 null=True, blank=True)
    name = models.CharField(max_length=255,
                            null=True, blank=True)
    characterid = models.IntegerField(null=True)
    corp = models.CharField(max_length=255,
                            null=True, blank=True)
    corpid = models.IntegerField(null=True)
    alliance = models.CharField(max_length=255,
                                null=True, blank=True)
    allianceid = models.IntegerField(null=True)
    last_check = models.DateTimeField(null=True)
    active = models.BooleanField(default=False)

    def __str__(self):
        return "User %i (%s)" % (self.mybb_uid, self.mybb_username)

    class Meta:
        ordering = ['mybb_username']

class AuthLog(models.Model):
    timestamp = models.DateTimeField(auto_now=True)
    corp = models.CharField(max_length=255, null=True)
    message = models.TextField()

    class Meta:
        ordering = ['-timestamp']

class AuthToken(models.Model):
    timestamp = models.DateTimeField(auto_now=True)
    user = models.OneToOneField(User)
    token = models.CharField(max_length=255)
