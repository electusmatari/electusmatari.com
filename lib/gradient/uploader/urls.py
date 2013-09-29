from django.conf.urls.defaults import *

urlpatterns = patterns('gradient.uploader.views',
  (r'^$', 'view_overview'),
  (r'^token/$', 'view_token'),
  (r'^files/(?P<filename>[^/]*)$', 'view_files'),
  (r'^auto/$', 'view_auto'),
  (r'^json/rpc/$', 'json_rpc'),
  (r'^json/rpc/check/$', 'json_check_auth_token'),
  (r'^json/rpc/submit/$', 'json_submit_cache_data'),
  (r'^json/rpc/exception/$', 'json_submit_exception'),
  (r'^json/suggest/markethistory/$', 'json_suggest_markethistory'),
  (r'^json/suggest/marketorders/$', 'json_suggest_marketorders'),
  (r'^json/suggest/corporations/$', 'json_suggest_corporations'),
)
