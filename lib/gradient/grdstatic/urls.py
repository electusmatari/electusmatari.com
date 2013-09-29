from django.conf.urls.defaults import *

from django.views.generic.simple import direct_to_template

urlpatterns = patterns('gradient.grdstatic.views',
  (r'^$', direct_to_template, {'template': 'gradient/about.html'}),
  (r'^recruitment/$', direct_to_template, {'template': 'gradient/recruitment.html'}),
  (r'^employees/$', 'employees'),
)
