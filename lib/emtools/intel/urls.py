from django.conf.urls.defaults import *

urlpatterns = patterns('emtools.intel.views',
    ('^$', 'view_overview'),
    ('^submit/$', 'view_submit'),
    ('^submit/pilots/$', 'view_submitpilots'),
    ('^search/$', 'view_search'),
    ('^search/ajax/entities/$', 'view_searchajax'),
    ('^search/ajax/systems/$', 'view_searchajaxsystems'),
    ('^tracking/$', 'view_tracking'),
    ('^pilot/(?P<name>.*)$', 'view_pilot'),
    ('^corp/(?P<name>.*)$', 'view_corp'),
    ('^alliance/(?P<name>.*)$', 'view_alliance'),
    ('^locators/$', 'view_locators'),
)
