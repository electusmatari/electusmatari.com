from django.conf.urls.defaults import *

urlpatterns = patterns('emtools.timezones.views',
    ('^config/$', 'view_config'),
    ('^', 'view_time'),
)
