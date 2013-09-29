from django.db import models
from django.contrib.auth.models import User

class Ticket(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    createdby = models.ForeignKey(User, related_name="createdticket_set")
    edited = models.DateTimeField(null=True, default=None)
    editedby = models.ForeignKey(User, null=True, default=None,
                                 related_name="editedticket_set")
    assigned = models.DateTimeField(null=True, default=None)
    assignedto = models.ForeignKey(User, null=True, default=None,
                                   related_name="assignedticket_set")
    closed = models.DateTimeField(null=True, default=None)
    delayeduntil = models.DateTimeField(null=True, default=None)
    state = models.ForeignKey('State')
    type = models.ForeignKey('TicketType')
    text = models.TextField()

    class Meta:
        ordering = ["created"]

class State(models.Model):
    name = models.CharField(max_length=32)
    displayname = models.CharField(max_length=32)

    def __unicode__(self):
        return self.displayname

    class Meta:
        ordering = ["id"]

class TicketType(models.Model):
    name = models.CharField(max_length=32)
    description = models.TextField()
    users = models.ManyToManyField(User)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ["name"]

class Comment(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User)
    ticket = models.ForeignKey(Ticket)
    text = models.TextField()

    class Meta:
        ordering = ["created"]

from django import forms

class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ('type', 'text')
