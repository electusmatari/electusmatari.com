from django.conf.urls.defaults import *

urlpatterns = patterns('emtools.fw.views',
    ('^$', 'view_topstats'),
    ('^map/$', 'view_map'),
    ('^corps/$', 'view_corps'),
    ('^changes/$', 'view_corpchanges'),
)
