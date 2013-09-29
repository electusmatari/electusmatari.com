from django.conf.urls.defaults import *

from django.views.generic.simple import direct_to_template

urlpatterns = patterns('gradient.index.views',
  (r'^$', 'index'),
  (r'^calculator/$', 'calculator'),
  (r'^help/$', direct_to_template, {'template': 'index/help.html'}),
)
