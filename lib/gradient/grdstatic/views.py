# Create your views here.

from django.views.generic.simple import direct_to_template

from gradient.decorators import require_gradient

@require_gradient
def employees(request):
    return direct_to_template(request, 'gradient/employees.html')
