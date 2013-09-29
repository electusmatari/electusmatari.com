from django.views.generic.simple import redirect_to
from django.conf.urls.defaults import *

urlpatterns = patterns('emtools.channels.views',
    ('^$', 'view_channels', {'category': 'mandatory'}),
    ('^mandatory/', redirect_to, {'url': '/tools/channels/'}),
    ('^(?P<category>alliance|intel|other|ooc|COA)/$', 'view_channels'),
    ('^edit/(?P<channelid>[0-9]+)/$', 'view_edit'),
    ('^changelog/$', 'view_changelog'),
)
