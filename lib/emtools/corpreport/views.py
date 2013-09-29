import json

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import redirect
from django.views.generic.simple import direct_to_template

from emtools.ccpeve.models import LastUpdated, Division
from emtools.ccpeve.models import Balance

from models import DivisionConfig, ReportCategory, PRODUCTION_CATEGORIES
from utils import get_locations
import forms

def view_balances(request):
    ownerid = request.user.profile.corpid
    corpname = request.user.profile.corp
    accountname = dict((row.accountKey, row.walletname)
                       for row in Division.objects.filter(ownerid=ownerid))
    qs = Balance.objects.filter(
        ownerid=ownerid,
        ).order_by("apitimestamp")
    rawdata = {}
    for row in qs:
        ts = row.apitimestamp
        rawdata.setdefault(ts, {})
        rawdata[ts][accountname[row.accountKey]] = row.balance
    plotdata = {}
    for div in Division.objects.filter(ownerid=ownerid):
        if div.divisionconfig.usewallet:
            plotdata[div.walletname] = []
    for ts, balances in sorted(rawdata.items()):
        for division in plotdata.keys():
            plotdata[division].append((jstimestamp(ts),
                                       int(rawdata[ts][division])))
    plotarg = []
    for division in plotdata.keys():
        d = {'label': division,
             'data': plotdata[division]}
        update_axes(d)
        plotarg.append(d)
    return direct_to_template(request, 'corpreport/balances.html',
                              extra_context={
            'tab': 'balances',
            'corpname': corpname,
            'plotdata': json.dumps(plotarg)
            })

def update_axes(flotarg):
    """
    Return the axis for the flot plot.
    """
    data = flotarg['data']
    if data[0][1] > 1e10:
        flotarg['yaxis'] = 2

def view_config(request):
    ownerid = request.user.profile.corpid
    corpname = request.user.profile.corp

    for division in Division.objects.filter(ownerid=ownerid,
                                            divisionconfig=None):
        DivisionConfig.objects.create(division=division,
                                      usehangar=False, usewallet=False)

    if request.method == 'POST':
        for division in Division.objects.filter(ownerid=ownerid):
            dc = division.divisionconfig
            for divisiontype in ['hangar', 'wallet']:
                enabled = request.POST.get(divisiontype +
                                           str(division.accountKey),
                                           False)
                setattr(dc,
                        "use" + divisiontype,
                        bool(enabled))
            dc.save()
        return redirect('corpreport-config')
    last_updated = LastUpdated.objects.filter(ownerid=ownerid).order_by("id")
    division_config = DivisionConfig.objects.filter(
        division__ownerid=ownerid
        ).order_by("division__accountKey")
    return direct_to_template(request, 'corpreport/config.html',
                              extra_context={'tab': 'config',
                                             'corpname': corpname,
                                             'last_updated': last_updated,
                                             'division_config': division_config})

def view_reportcategories(request, category=None):
    ownerid = request.user.profile.corpid
    corpname = request.user.profile.corp
    
    if category is None:
        return direct_to_template(request,
                                  'corpreport/reportcategory_choose.html',
                                  extra_context={
                'tab': 'categories',
                'corpname': corpname,
                'not_reported_count': ReportCategory.objects.filter(
                    category=None).count(),
                'category_list': [(cat, ReportCategory.objects.filter(
                            category=cat).count())
                                  for cat in PRODUCTION_CATEGORIES]})

    if request.method == 'POST':
        typeid = request.POST.get('typeID')
        new_category = request.POST.get('category')
        if new_category not in PRODUCTION_CATEGORIES:
            return redirect('corpreport-categories-choose')
        try:
            repcat = ReportCategory.objects.get(type__typeID=typeid)
        except ReportCategory.DoesNotExist:
            return redirect('corpreport-categories-choose')
        repcat.category = new_category
        repcat.save()
        return redirect(request.build_absolute_uri())
    form_list = []
    if category == 'Not Reported':
        category = None
    for repcat in ReportCategory.objects.filter(
        category=category
        ).select_related(
        'type__group__category'
        ).order_by('type__typeName'):
        form_list.append((repcat, forms.ReportCategoryForm(instance=repcat)))
    paginator = Paginator(form_list, 100)
    try:
        page = paginator.page(int(request.GET.get('page', '1')))
    except (ValueError, PageNotAnInteger):
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)
    return direct_to_template(request,
                              'corpreport/reportcategory_list.html',
                              extra_context={'tab': 'categories',
                                             'corpname': corpname,
                                             'category': category,
                                             'is_paginated': True,
                                             'page_obj': page,
                                             'paginator': paginator,
                                             'form_list': page.object_list})

def view_locations(request):
    ownerid = request.user.profile.corpid
    corpname = request.user.profile.corp
    
    (sales_center, logistics_center, offices,
     sales_points, purchase_points) = get_locations(ownerid)

    return direct_to_template(request, 'corpreport/locations.html',
                              extra_context={
            'tab': 'locations',
            'corpname': corpname,
            'sales_center': sorted(sales_center, key=lambda s: s.stationName),
            'logistics_center': sorted(logistics_center,
                                       key=lambda s: s.stationName),
            'offices': sorted(offices, key=lambda s: s.stationName),
            'sales_points': sorted(sales_points, key=lambda s: s.stationName),
            'purchase_points': sorted(purchase_points,
                                      key=lambda s: s.stationName),
            })

from time import mktime
def jstimestamp(dt):
    unixtime = mktime(dt.timetuple()) + 1e-6 * dt.microsecond
    return int(unixtime * 1000)
