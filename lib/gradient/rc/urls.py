from django.conf.urls.defaults import *

from django.views.generic.list_detail import object_list
from gradient.rc.models import Change

urlpatterns = patterns('',
  (r'^$', object_list, {'queryset': Change.objects.all(),
                        'paginate_by': 23,
                        'template_object_name': 'change'}),
)
