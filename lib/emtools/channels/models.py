from django.db import models
from django.contrib.auth.models import User

import emtools.ccpeve.igb as igb


class Channel(models.Model):
    category = models.CharField(max_length=128)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField()

    def join_button(self):
        return igb.JoinChannel(self.name, "Join")

    def __str__(self):
        return "%s (%s)" % (self.name, self.category.title())

    class Meta:
        ordering = ["name"]

class ChangeLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User)
    channel = models.CharField(max_length=255)
    action = models.CharField(max_length=255)

    class Meta:
        ordering = ["-timestamp"]
