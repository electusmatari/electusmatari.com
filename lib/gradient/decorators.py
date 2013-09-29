from functools import wraps
from django.shortcuts import redirect
from django.views.generic.simple import direct_to_template

def require_gradient(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if (request.user.is_anonymous() or
            request.user.profile is None or
            request.user.profile.corp != 'Gradient'):
            return direct_to_template(request, 'gradient/authrequired.html')
        else:
            return func(request, *args, **kwargs)
    return wrapper
