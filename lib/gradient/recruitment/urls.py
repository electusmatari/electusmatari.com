from django.conf.urls.defaults import *

from django.views.generic.simple import direct_to_template

urlpatterns = patterns('gradient.recruitment.views',
  (r'^$', direct_to_template, {'template': 'recruitment/index.html'}),
  (r'^apply/$', 'apply_view'),
  (r'^apply/(?P<page>[0-9]+)/$', 'questionnaire'),
)
