import json

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic.simple import direct_to_template

from emtools.ccpeve.models import Type

from build import cost, build
from models import BlueprintOriginal

def view_bpos(request):
    ownerid = request.user.profile.corpid
    corpname = request.user.profile.corp
    qs = BlueprintOriginal.objects.filter(
        ownerid=ownerid).order_by('blueprint__typeName')
    return direct_to_template(request, 'industry/bpos.html',
                              extra_context={
            'tab': 'bpos',
            'corpname': corpname,
            'blueprint_list': qs
            })

def view_build(request, typename):
    ownerid = request.user.profile.corpid
    corpname = request.user.profile.corp

    t = get_object_or_404(Type, typeName=typename)
    basket = build(ownerid, t)
    if basket is None or len(basket) == 0:
        return direct_to_template(request, 'industry/build_direct.html',
                                  extra_context={
                'tab': 'build',
                'corpname': corpname,
                'typename': t.typeName,
                'totalcost': cost(ownerid, t)})
    components = []
    for type_, quantity in basket.items():
        pu = cost(ownerid, type_)
        components.append((type_, quantity, pu, pu * quantity))
    components.sort(key=lambda x: x[0].typeName)
    totalcost = sum(x[1] * x[2] for x in components)
    return direct_to_template(request, 'industry/build_detail.html',
                              extra_context={
            'tab': 'build',
            'corpname': corpname,
            'typename': t.typeName,
            'component_list': components,
            'totalcost': totalcost,
            'source': basket.note,
            })

def view_search(request):
    typeq = Type.objects.filter(published=1).exclude(marketGroupID=None)
    if 'q' in request.GET:
        q = request.GET['q']
        try:
            type_ = typeq.get(typeName=q)
        except Type.DoesNotExist:
            pass
        else:
            return redirect('industry-build', type_.typeName)
        type_list = typeq.filter(typeName__icontains=request.GET['q'])
    else:
        type_list = []
    if len(type_list) == 1:
        return redirect('industry-build', type_list[0].typeName)
    return direct_to_template(request, 'industry/build.html',
                              extra_context={
            'tab': 'build',
            'type_list': type_list,
            })

def view_search_ajax(request):
    typeq = Type.objects.filter(published=1).exclude(marketGroupID=None)
    term = request.GET.get("term", "")
    result = []
    for type_ in typeq.filter(typeName__icontains=term):
        result.append({'label': type_.typeName,
                       'value': type_.typeName,
                       'type': 'invtype'})
    result.sort(key=lambda x: x['label'].lower())
    return HttpResponse(json.dumps(result), mimetype='text/plain')
