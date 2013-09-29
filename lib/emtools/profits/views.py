from django.db import connection
from django.views.generic.simple import direct_to_template

from emtools.emauth.decorators import require_mybbgroup

from gradient.index.models import Index

ORE_NOTES = {
    'Veldspar': "High-Sec (1.0)",
    'Concentrated Veldspar': "High-Sec (1.0)",
    'Dense Veldspar': "High-Sec (1.0)",
    'Scordite': "High-Sec (1.0)",
    'Condensed Scordite': "High-Sec (1.0)",
    'Massive Scordite': "High-Sec (1.0)",
    'Plagioclase': "High-Sec (0.9)",
    'Azure Plagioclase': "High-Sec (0.9)",
    'Rich Plagioclase': "High-Sec (0.9)",
    'Pyroxeres': "Amarr/Caldari High-Sec (0.9)",
    'Solid Pyroxeres': "Amarr/Caldari High-Sec (0.9)",
    'Viscous Pyroxeres': "Amarr/Caldari High-Sec (0.9)",
    'Omber': "High-Sec (0.7)",
    'Silvery Omber': "High-Sec (0.7)",
    'Golden Omber': "High-Sec (0.7)",
    'Kernite': "Low-Sec (0.4), Amarr High-Sec (0.7)",
    'Luminous Kernite': "Low-Sec (0.4), Amarr High-Sec (0.7)",
    'Fiery Kernite': "Low-Sec (0.4), Amarr High-Sec (0.7)",
    'Jaspet': "Amarr/Gallente Low-Sec (0.4)",
    'Pure Jaspet': "Amarr/Gallente Low-Sec (0.4)",
    'Pristine Jaspet': "Amarr/Gallente Low-Sec (0.4)",
    'Gneiss': "Null-Sec",
    'Iridescent Gneiss': "Null-Sec",
    'Prismatic Gneiss': "Null-Sec",
    'Hedbergite': "Low-Sec (0.2)",
    'Vitric Hedbergite': "Low-Sec (0.2)",
    'Glazed Hedbergite': "Low-Sec (0.2)",
    'Hemorphite': "Amarr/Gallente Low-Sec (0.2)",
    'Vivid Hemorphite': "Amarr/Gallente Low-Sec (0.2)",
    'Radiant Hemorphite': "Amarr/Gallente Low-Sec (0.2)",
    'Spodumain': "Null-Sec",
    'Bright Spodumain': "Null-Sec",
    'Gleaming Spodumain': "Null-Sec",
    'Dark Ochre': "Null-Sec",
    'Onyx Ochre': "Null-Sec",
    'Obsidian Ochre': "Null-Sec",
    'Crokite': "Null-Sec",
    'Bistot': "Null-Sec",
    'Sharp Crokite': "Null-Sec",
    'Triclinic Bistot': "Null-Sec",
    'Crystalline Crokite': "Null-Sec",
    'Monoclinic Bistot': "Null-Sec",
    'Arkonor': "Null-Sec",
    'Crimson Arkonor': "Null-Sec",
    'Prime Arkonor': "Null-Sec",
    'Mercoxit': "Null-Sec",
    'Magma Mercoxit': "Null-Sec",
    'Vitreous Mercoxit': "Null-Sec",
    'Glacial Mass': "Minmatar High-Sec",
    'Smooth Glacial Mass': "Minmatar Low-Sec",
    'White Glaze': "Caldari, High-Sec",
    'Pristine White Glaze': "Caldari Low-Sec",
    'Blue Ice': "Gallente High-Sec",
    'Thick Blue Ice': "Gallente Low-Sec",
    'Clear Icicle': "Amarr High-Sec",
    'Enriched Clear Icicle': "Amarr Low-Sec",
    'Krystallos': "Strontium Clathare rich",
    'Glare crust': "Heavy Water rich",
    'Gelidus': "",
    'Dark Glitter': "Liquid Ozone rich",
    }

@require_mybbgroup('Electus Matari')
def view_ore(request, ice=False):
    c = connection.cursor()
    c.execute("SELECT t.typename, g.groupname, t.volume, t.portionsize, "
              "       m.quantity, mt.typename "
              "FROM ccp.invtypes t "
              "     INNER JOIN ccp.invgroups g ON t.groupid = g.groupid "
              "     INNER JOIN ccp.invcategories c "
              "       ON g.categoryid = c.categoryid "
              "     INNER JOIN ccp.invtypematerials m ON t.typeid = m.typeid "
              "     INNER JOIN ccp.invtypes mt "
              "       ON m.materialtypeid = mt.typeid "
              "WHERE c.categoryname = 'Asteroid' "
              "  AND t.typename NOT LIKE 'Compressed %' "
              "  AND t.published = 1")
    index = get_index(request)
    prices = {}
    groups = {}
    bad = set()
    for ore, group, volume, portionsize, quantity, mineral in c.fetchall():
        if ore in bad:
            continue
        prices.setdefault(ore, 0)
        if mineral not in index:
            del prices[ore]
            bad.add(ore)
        prices[ore] += ((quantity * index[mineral]) / (float(volume * portionsize)))
        groups[ore] = group
    prices = prices.items()
    prices.sort(key=lambda v: v[1])
    ore_list = []
    for ore, price in prices:
        if ice and groups[ore] != 'Ice':
            continue
        if not ice and 'full' not in request.GET and ore != groups[ore]:
            continue
        ore_list.append({'name': ore,
                         'price': price,
                         'notes': ORE_NOTES.get(ore, "")})
    return direct_to_template(request, 'profits/ore.html',
                              extra_context={'tab': 'ice' if ice else 'ore',
                                             'ice': ice,
                                             'ore_list': ore_list,
                                             'location': request.GET.get('location', 'Republic'),
                                             'full': request.GET.get('full', 'false')})

def get_index(request):
    location = request.GET.get('location', 'Republic')
    if location == 'Jita':
        return dict((index.typename, index.jita)
                    for index in Index.objects.all())
    elif location == 'Rens':
        return dict((index.typename, index.heimatar)
                    for index in Index.objects.all())
    else:
        return dict((index.typename, index.republic)
                    for index in Index.objects.all())
