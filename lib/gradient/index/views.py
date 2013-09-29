import csv
import json
import StringIO
import xml.etree.ElementTree as ET

from django.http import HttpResponse
from django.views.generic.simple import direct_to_template

from gradient.index.models import Index

def index(request):
    format = request.GET.get('format', 'html')
    if format == 'csv':
        return index_csv(request)
    elif format == 'xml':
        return index_xml(request)
    else:
        return direct_to_template(request, 'index/index.html',
                                  extra_context={'index_list': 
                                                 Index.objects.all()})

def index_csv(request):
    current_category = None
    out = StringIO.StringIO()
    writer = csv.writer(out)
    first = True
    for row in Index.objects.all():
        if row.category != current_category:
            if first:
                writer.writerow(['Typename', 'Index', 'Change', 'Volume',
                                 'Heimatar', 'Metropolis', 'Molden Heath',
                                 'Jita'])
                first = False
            else:
                writer.writerow([''] * 8)
            writer.writerow([row.category] + [''] * 7)
            current_category = row.category
        writer.writerow([row.typename,
                         "%.2f" % row.republic,
                         "%+.2f" % row.republicchange,
                         row.republicvolume,
                         "%.2f" % row.heimatar,
                         "%.2f" % row.metropolis,
                         "%.2f" % row.moldenheath,
                         "%.2f" % row.jita])
    out.seek(0)
    return HttpResponse(out.read(), content_type="text/plain")

def index_xml(request):
    root = ET.Element("index")
    timestamp = None
    for entry in Index.objects.all():
        typeelt = ET.SubElement(root, "type")
        timestamp = entry.timestamp
        typeelt.set("name", entry.typename)
        typeelt.set("typeid", str(entry.typeid))
        typeelt.set("republic", str(entry.republic))
        typeelt.set("republicvolume", str(entry.republicvolume))
        typeelt.set("republicchange", str(entry.republicchange))
        typeelt.set("heimatar", str(entry.heimatar))
        typeelt.set("heimatarvolume", str(entry.heimatarvolume))
        typeelt.set("heimatarchange", str(entry.heimatarchange))
        typeelt.set("metropolis", str(entry.metropolis))
        typeelt.set("metropolisvolume", str(entry.metropolisvolume))
        typeelt.set("metropolischange", str(entry.metropolischange))
        typeelt.set("moldenheath", str(entry.moldenheath))
        typeelt.set("moldenheathvolume", str(entry.moldenheathvolume))
        typeelt.set("moldenheathchange", str(entry.moldenheathchange))
        typeelt.set("jita", str(entry.jita))
        typeelt.set("jitavolume", str(entry.jitavolume))
        typeelt.set("jitachange", str(entry.jitachange))
    root.set("timestamp", timestamp.strftime("%Y-%m-%d"))
    tree = ET.ElementTree(root)
    out = StringIO.StringIO()
    tree.write(out)
    out.seek(0)
    return HttpResponse(out.read(), content_type="text/xml")

def calculator(request):
    prices = []
    for row in Index.objects.all():
        prices.append({'name': row.typename,
                       'value': row.republic,
                       'type': row.category})
    return direct_to_template(request, 'index/calculator.html',
                              extra_context={'jsondata': json.dumps(prices)})
