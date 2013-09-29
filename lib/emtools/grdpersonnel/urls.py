from django.conf.urls.defaults import *

urlpatterns = patterns('emtools.grdpersonnel.views',
    ('^$', 'view_members'),
)
