from django import forms
from emtools.channels.models import Channel

class ChannelForm(forms.ModelForm):
    class Meta:
        model = Channel
        exclude = ['category']
