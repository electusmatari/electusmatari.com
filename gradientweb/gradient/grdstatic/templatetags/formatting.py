import re

from django.utils.encoding import force_unicode
from django import template

register = template.Library()

@register.filter
def floatcomma(value):
    try:
        orig = force_unicode("%.2f" % float(value))
    except ValueError:
        return value
    new = re.sub("^(-?\d+)(\d{3})", '\g<1>,\g<2>', orig)
    while orig != new:
        orig = new
        new = re.sub("^(-?\d+)(\d{3})", '\g<1>,\g<2>', orig)
    return new

def intcomma(value):
    """
    Converts an integer to a string containing commas every three digits.
    For example, 3000 becomes '3,000' and 45000 becomes '45,000'.
    """
    orig = force_unicode(value)
    new = re.sub("^(-?\d+)(\d{3})", '\g<1>,\g<2>', orig)
    if orig == new:
        return new
    else:
        return intcomma(new)
intcomma.is_safe = True
register.filter(intcomma)

@register.filter
def percentagechange(decimal):
    if decimal is None:
        return ""
    else:
        return "%+.2f%%" % ((float(decimal) - 1)*100)

@register.filter
def percentage(decimal):
    if decimal is None:
        return ""
    else:
        return "%.1f%%" % (float(decimal)*100)

@register.filter
def setpage(value, arg):
    d = arg.GET.copy()
    d['page'] = value
    return d.urlencode()

@register.filter
def itemdb(value):
    return value.replace(" ", "_")

@register.filter
def format(value, fmt):
    return fmt %  value

@register.filter
def truncatechars(value, count):
    value = str(value)
    if len(value) > count:
        return value[:count-3] + "..."
    else:
        return value

