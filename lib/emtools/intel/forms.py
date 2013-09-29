import datetime
import re

from django import forms
from emtools.intel.models import Trace

class TraceForm(forms.Form):
    message = forms.CharField(widget=forms.widgets.Textarea(),
                              label='Trace')
    online = forms.NullBooleanField(label="On Comms")

    def clean_message(self):
        message = self.cleaned_data['message'].replace("\r", "")
        match = TRACE_RX.match(message)
        if match is None:
            if "in your solar system" in message:
                raise forms.ValidationError("Sadly, we do not accept traces for targets in the current solar system")
            else:
                raise forms.ValidationError("Malformed trace mail, please submit the full message from your agent")
        self.cleaned_data['target'] = match.group('target')
        self.cleaned_data['agent'] = match.group('agent')
        try:
            self.cleaned_data['timestamp'] = datetime.datetime.strptime(match.group('ts'),
                                                                        "%Y.%m.%d %H:%M")
        except ValueError:
            self.cleaned_data['timestamp'] = datetime.datetime.strptime(match.group('ts'),
                                                                        "%Y.%m.%d")
        self.cleaned_data['station'] = match.group('station')
        self.cleaned_data['system'] = match.group('system')

TRACE_RX = re.compile("I found (?P<target>.*?) for you\n"
                      "From: *(?P<agent>.*?)\n"
                      "Sent: *(?P<ts>[0-9][0-9][0-9][0-9]\\.[0-9][0-9]\\.[0-9][0-9](?: [0-9][0-9]:[0-9][0-9])?).*\n"
                      "\n"
                      "The (?:sleazebag is currently|scumsucker is located) "
                      "(?:at (?P<station>.*?) station )?"
                      "in the (?P<system>.*?) system.*")

TRACE_RX = re.compile("I found (?P<target>.*?) for you.\n"
                      "From: *(?P<agent>.*?)\n"
                      "Sent: *(?P<ts>[0-9][0-9][0-9][0-9]\\.[0-9][0-9]\\.[0-9][0-9](?: [0-9][0-9]:[0-9][0-9])?).*\n"
                      "\n"
                      "I've found your .*.\n"
                      "\n"
                      "(?:She|He) is "
                      "(?:at (?P<station>.*?) station )?"
                      "in the (?P<system>.*?) system.*")
