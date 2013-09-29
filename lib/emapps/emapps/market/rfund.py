# Reimbursementfund display

import cgi
import csv

import kgi
from emapps.util import require_permission, humane

csvfile = "/home/forcer/Projects/old-emcom/ftp/data/reimbursementfund.csv"

@require_permission('em')
def view_rfund(environ):
    user = environ["emapps.user"]

    categories = {}

    for typename, category, quantity in csv.reader(file(csvfile)):
        if category not in categories:
            categories[category] = []
        categories[category].append((typename, humane(int(quantity))))

    cats = categories.keys()
    cats.sort()

    data = []
    for cat in cats:
        types = categories[cat]
        types.sort()
        data.append((cat, types))

    return kgi.template_response('market/reimbursementfund.html',
                                 user=user,
                                 data=data)
