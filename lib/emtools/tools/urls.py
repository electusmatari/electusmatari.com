from django.conf.urls.defaults import *

urlpatterns = patterns('emtools.tools.views',
    ('^test/', 'view_test'),
    ('^$', 'view_tools'),
)
