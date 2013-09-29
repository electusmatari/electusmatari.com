import logging
import random

from django.http import HttpResponseRedirect
from django.views.generic.simple import direct_to_template

from emtools.emauth.decorators import require_mybbgroup

log = logging.getLogger('tools')

TOOLS = [
    ('Public',
     [('/auth/', 'Authentication', '/media/img/tools/auth.png'),
      ('/standings/', 'Standings', '/media/img/tools/standings.png'),
      ('http://gradient.electusmatari.com/index/', 'Material Index',
       '/media/img/tools/gmi.png'),
      ])
    ]
EMTOOLS = [
    ('Alliance',
     [('/tools/channels/', 'Channels', '/media/img/tools/channels.png'),
      ('/tools/profits/', 'Profits', '/media/img/tools/profits.png'),
      ('/vote/', 'Vote', '/media/img/tools/vote.png'),
      ('/gallery/', 'Gallery', '/media/img/tools/gallery.png'),
      ('/intel/', 'Intel', '/media/img/tools/intel.png'),
      ('/market/reimbursementfund/', 'Reimbursement Fund',
       '/media/img/tools/reimbursementfund.png'),
      ('/tools/timezones/', '(( Timezones ))',
       '/media/img/tools/timezones.png'),
      ('/fw/', 'Factional Warfare',
       '/media/img/tools/fw.png'),
      ]),
    ('Restricted',
     [('/corpadmin/', 'Corp Admin', '/media/img/tools/corpadmin.png'),
      ('/admin/', 'Site Admin', '/media/img/tools/admin.png'),
      ])
    ]

GRDTOOLS = [
    ('Gradient',
     [('http://gradient.electusmatari.com/', 'Gradient',
       '/media/img/tools/gradient.png'),
      ])
    ]

def view_tools(request):
    tools = TOOLS[:]
    if request.user.is_authenticated():
        if 'Electus Matari' in request.user.profile.mybb_groups:
            tools.extend(EMTOOLS)
        if 'Gradient' in request.user.profile.mybb_groups:
            tools.extend(GRDTOOLS)
    return direct_to_template(request, 'tools/index.html',
                              extra_context={'tools': tools})

##################################################################
### Banner

BANNER_URLS = [(0.27127659574468083, 'http://www.electusmatari.com/media/img/banner/Rifter__Tiger_Phoenix.png'),
               (0.27127659574468083, 'http://www.electusmatari.com/media/img/banner/Electus_Matari__Misla_Khalren.png'),
               (0.19148936170212766, 'http://www.electusmatari.com/media/img/banner/Angry_Wolf__Gahrian_Ketar.jpg'),
               (0.19148936170212766, 'http://www.electusmatari.com/media/img/banner/Never_Again__Karagh.png'),
               (0.074468085106382961, 'http://www.electusmatari.com/media/img/banner/Hurricane__Ackercoke.png')]

def view_banner(request):
    roll = random.random()
    p = 0
    for thisp, url in BANNER_URLS:
        p += thisp
        if roll <= p:
            return HttpResponseRedirect(url)
    log.warning("Banner probability does not sum up to 1 (%s)" % roll)
    return HttpResponseRedirect(BANNER_URLS[0][1])

##################################################################
### Testing

def view_test(request):
    return direct_to_template(request, 'tools/test.html',
                              extra_context={'test': request.igb})
