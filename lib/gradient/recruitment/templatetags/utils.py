from django import template

register = template.Library()

@register.filter
def dictget(value, arg):
    return value.get(arg, "")
