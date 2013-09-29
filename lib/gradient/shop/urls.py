from django.conf.urls.defaults import *

urlpatterns = patterns('gradient.shop.views',
  (r'^$', 'index_view'),
  (r'^auth/$', 'auth_view'),
  (r'^cart/$', 'cart_view'),
  (r'^order/$', 'order_view'),
  (r'^messages/$', 'messages_view'),
  (r'^handle/$', 'handle_view'),
  (r'^handle/messages/$', 'handle_messages_view'),
  (r'^handle/messages/(?P<characterid>[0-9]+)/$', 'handle_messages_view'),
  (r'^handle/orders/$', 'handle_closed_view'),
  (r'^json/split/$', 'handle_split'),
#  (r'^handle/(?P<orderid>[0-9]+)/edit/$', 'order_edit'),
)
