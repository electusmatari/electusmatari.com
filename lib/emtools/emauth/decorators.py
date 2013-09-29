from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.utils.http import urlquote

def require_account(view_func):
    def view(request, *args, **kwargs):
        if request.user.is_authenticated():
            return view_func(request, *args, **kwargs)
        else:
            return HttpResponseRedirect("%s&url=%s" % (
                    settings.LOGIN_URL,
                    urlquote(request.build_absolute_uri())))
    return view

def require_mybbgroup(groupname):
    if isinstance(groupname, (list, tuple)):
        required_groups = groupname
    else:
        required_groups = [groupname]
    def wrapper(orig_view):
        def new_view(request, *args, **kwargs):
            if not request.user.is_authenticated():
                raise PermissionDenied()
            if request.user.is_superuser:
                return orig_view(request, *args, **kwargs)
            if not hasattr(request.user, 'profile'):
                raise PermissionDenied()
            if 'Banned' in request.user.profile.mybb_groups:
                raise PermissionDenied()
            for groupname in required_groups:
                if groupname in request.user.profile.mybb_groups:
                    return orig_view(request, *args, **kwargs)
            raise PermissionDenied()
        return new_view
    return wrapper

def require_admin(fun):
    def wrapper(request, *args, **kwargs):
        if request.user.is_staff:
            return fun(request, *args, **kwargs)
        else:
            raise PermissionDenied()
    return wrapper

