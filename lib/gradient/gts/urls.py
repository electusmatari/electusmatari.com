from django.conf.urls.defaults import *

from django.views.generic.simple import direct_to_template

urlpatterns = patterns('gradient.gts.views',
  (r'^$', 'list'),
  (r'^(?P<ticketid>[0-9]+)/$', 'details'),
  (r'^create/$', 'create'),
  (r'^(?P<ticketid>[0-9]+)/edit/$', 'create'),
  (r'^(?P<ticketid>[0-9]+)/accept/$', 'accept'),
  (r'^(?P<ticketid>[0-9]+)/close/$', 'close'),
  (r'^(?P<ticketid>[0-9]+)/reopen/$', 'reopen'),
  (r'^(?P<ticketid>[0-9]+)/comment/$', 'add_comment'),
  (r'^configuration/$', 'config'),
  (r'^help/$', 'help'),
)
