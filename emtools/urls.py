from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    ('^auth/', include('emtools.emauth.urls')),
    ('^admin/', include('emtools.emadmin.urls')),
    ('^corpadmin/', include('emtools.corpadmin.urls')),
    ('^intel/', include('emtools.intel.urls')),
    ('^gmi/', include('emtools.gmi.urls')),
    ('^gmi2/', include('emtools.gmi.urls')),

    ('^tools/channels/', include('emtools.channels.urls')),
    ('^tools/timezones/', include('emtools.timezones.urls')),
    ('^tools/fw/', include('emtools.fw.urls')),
    ('^tools/', include('emtools.tools.urls')),
    ('^banner/', 'emtools.tools.views.view_banner'),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    (r'^_admin/(.*)', admin.site.root),
)
