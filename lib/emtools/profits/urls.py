from django.conf.urls.defaults import *

urlpatterns = patterns('emtools.profits.views',
    ('^$', 'view_ore'),
    ('^ice/$', 'view_ore', {'ice': True}),
)
