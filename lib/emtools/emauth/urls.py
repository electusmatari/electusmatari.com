from django.conf.urls.defaults import *

urlpatterns = patterns('emtools.emauth.views',
    ('^$', 'view_main'),
    ('^avatar/$', 'view_avatar'),
    ('^token/$', 'view_token'),
)
