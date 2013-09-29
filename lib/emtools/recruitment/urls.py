from django.conf.urls.defaults import *

urlpatterns = patterns('emtools.recruitment.views',
    ('^audits/(?P<userid>[0-9]+)/$', 'view_single_audit'),
    ('^audits/$', 'view_audits'),
    ('^$', 'view_submit'),
)
