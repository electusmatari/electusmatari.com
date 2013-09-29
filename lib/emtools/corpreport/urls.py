from django.conf.urls.defaults import *

urlpatterns = patterns('emtools.corpreport.views',
    url('^$', 'view_balances', name='corpreport-balances'),
    url('^locations/$', 'view_locations', name='corpreport-locations'),
    url('^categories/$', 'view_reportcategories',
        name='corpreport-category-choose'),
    url('^categories/(?P<category>[^/]*)/$', 'view_reportcategories',
        name='corpreport-category-list'),
    url('^config/$', 'view_config', name='corpreport-config'),
)
