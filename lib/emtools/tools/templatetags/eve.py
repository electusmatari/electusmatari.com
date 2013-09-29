import datetime

from django import template

register = template.Library()

@register.filter
def eve_time(value, format="%Y.%m.%d %H:%M"):
    if value is None or value == '':
        value = datetime.datetime.utcnow()
    year = value.year - 1898
    format = format.replace("%Y", "%s" % year)
    return value.strftime(str(format))
