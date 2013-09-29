from django import forms
from emtools.timezones.models import TZConfig

import os
import dateutil.tz as tz

def get_timezones():
    result = []
    for basepath in tz.TZPATHS:
        for dirpath, dirnames, filenames in os.walk(basepath):
            for fname in filenames:
                name = os.path.relpath(os.path.join(dirpath, fname),
                                       basepath)
                if (name.startswith("Etc/") or name.startswith("posix/") or
                    name.startswith("right") or name.endswith(".tab") or
                    name in ('localtime', 'posixrules')):
                    continue
                result.append(name)
    result.sort()
    return result

class TZField(forms.ChoiceField):
    def __init__(self, *args, **kwargs):
        kwargs['choices'] = [(x, x) for x in get_timezones()]
        super(TZField, self).__init__(*args, **kwargs)

class TZConfigForm(forms.ModelForm):
    timezone = TZField()
    class Meta:
        model = TZConfig
        exclude = ["user"]
