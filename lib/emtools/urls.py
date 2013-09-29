from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    ('^auth/', include('emtools.emauth.urls')),
    ('^admin/', include('emtools.emadmin.urls')),
    ('^corpadmin/', include('emtools.corpadmin.urls')),
    ('^intel/', include('emtools.intel.urls')),
    ('^recruitment/', include('emtools.recruitment.urls')),

    ('^fw/', include('emtools.fw.urls')),
    ('^tools/channels/', include('emtools.channels.urls')),
    ('^tools/timezones/', include('emtools.timezones.urls')),
    ('^tools/profits/', include('emtools.profits.urls')),
    ('^notify/', include('emtools.notify.urls')),
    ('^tools/', include('emtools.tools.urls')),
    ('^banner/', 'emtools.tools.views.view_banner'),

    ('^grd/personnel/', include('emtools.grdpersonnel.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # (r'^_admin/(.*)', admin.site.root),
)
