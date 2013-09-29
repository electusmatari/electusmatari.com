from django.conf.urls.defaults import *

urlpatterns = patterns('emtools.emadmin.views',
    ('^$', 'view_log'),
    ('^status/', 'view_status'),
    ('^groups/', 'view_groups'),
    ('^statistics/', 'view_stats'),
)
