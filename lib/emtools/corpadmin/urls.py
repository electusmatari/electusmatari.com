from django.conf.urls.defaults import *

urlpatterns = patterns('emtools.corpadmin.views',
    ('^$', 'view_authlog'),
    ('^members/$', 'view_members'),
    ('^activity/$', 'view_activity'),
    ('^apiconfig/$', 'view_apiconfig'),
    ('^ajax/$', 'view_ajax'),
)
