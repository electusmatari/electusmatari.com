from django.db import models
from django.contrib.auth.models import User

class Change(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    app = models.CharField(max_length=32)
    category = models.CharField(max_length=32)
    text = models.TextField()

    class Meta:
        ordering = ["-timestamp"]

