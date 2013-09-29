from django.conf.urls.defaults import *

urlpatterns = patterns('emtools.notify.views',
    ('^json/opnotify/$', 'json_opnotify'),
    ('^json/status/$', 'json_status'),
    ('^notsupported/$', 'notsupported'),
)
