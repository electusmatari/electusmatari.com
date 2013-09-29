from django.conf.urls.defaults import *

urlpatterns = patterns('emtools.industry.views',
    url('^bpos/$', 'view_bpos', name='industry-bpos'),
    url('^build/$', 'view_search', name='industry-build'),
    url('^build/(.*)/$', 'view_build', name='industry-build'),
    url('^search/$', 'view_search', name='industry-search'),
    url('^search/ajax/types/$', 'view_search_ajax',
        name='industry-ajax-search'),
)
