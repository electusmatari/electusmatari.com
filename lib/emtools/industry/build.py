# This likely needs a re-think for invention/reverse engineering
#
# build(Jaguar) => list of baskets
#
# Each basket has a special "blueprint" in it, actually, a
# blueprint/decryptor combination. Decryptor can be None for no
# decryptor, or False for BPO. (Or should it return tuples of
# blueprint, item?)
#
# T3 also is wrong. Component reverse engineering yields a random
# blueprint!

from django.db import connection

from emtools.gmi.models import Index
from emtools.ccpeve.models import Type, BlueprintType
from models import BlueprintOriginal

class ISKType(object):
    typeName = 'ISK'

def verbose(fun):
    def wrapper(*args, **kwargs):
        rv = fun(*args, **kwargs)
        print "%s%r = %r" % (fun.__name__, args, rv)
        return rv
    return wrapper

def cost(ownerid, invtype, do_reprocess=False):
    if invtype == ISKType:
        return AnnotatedFloat(1.00, 'Varies')
    try:
        return AnnotatedFloat(Index.objects.get(
                latest__typeid=invtype.typeID
                ).latest.republic,
                              'Index')
    except Index.DoesNotExist:
        pass
    basket = build(ownerid, invtype)
    if basket is not None:
        return basketcost(ownerid, basket)
    basecost = basepricecost(invtype)
    if basecost is not None:
        return AnnotatedFloat(basecost, 'Market')
    if do_reprocess:
        return basketcost(ownerid, reprocess(ownerid, invtype))
    return AnnotatedFloat(0.0, 'Unknown')

def basepricecost(invtype):
    c = connection.cursor()
    c.execute("SELECT corporationid FROM ccp.crpnpccorporationtrades "
              "WHERE typeid = %s",
              (invtype.typeID,))
    if c.rowcount > 0:
        return invtype.basePrice * 0.9
    else:
        return None

def basketcost(ownerid, basket):
    value = sum(cost(ownerid, invtype) * quantity
                for invtype, quantity in basket.items())
    return AnnotatedFloat(value, note=basket.note)

def reprocess(invtype):
    b = Basket(note='Reprocessing')
    for tm in invtype.typematerial_set.all():
        b[tm.materialType] = tm.quantity
    return b

def build(ownerid, invtype):
    # Blueprint
    try:
        blueprint = invtype.producedBy
    except BlueprintType.DoesNotExist:
        pass
    else:
        return build_from_blueprint(ownerid, invtype, blueprint)
    # Reaction
    b = build_from_reaction(ownerid, invtype)
    if b is not None:
        return b
    # Faction ammo
    if (invtype.group.groupName == 'Projectile Ammo' and
        invtype.typeName.startswith('Republic Fleet ')):
        size = int(invtype.attribute("chargeSize"))
        if size in (1, 2, 3): # Could be XL :-(
            extra_cost = [0, 480, 640, 960][size]
            return (build(ownerid, invtype.metatype.parentType) +
                    Basket({ISKType: extra_cost},
                           note='LP Store'))
    # Blueprint
    if invtype.group.category.categoryName == 'Blueprint':
        try:
            BlueprintOriginal.objects.get(ownerid=ownerid,
                                          blueprint=invtype)
        except BlueprintOriginal.DoesNotExist:
            pass
        else:
            return Basket(note='Owned BPO') # We have the BPO
        if invtype.group.groupName == 'Booster Blueprints':
            # 250k per run, see Damian
            return Basket({ISKType: 250000.0},
                          note='Contracts')

        tl = int(invtype.attribute('techLevel'))
        if tl == 1:
            return Basket(note='T1 BPO') # T1 BP cost "nothing"
        elif tl == 2:
            return invent(invtype)
        elif tl == 3:
            return [reverseengineer(invtype)]
    return None

def build_from_blueprint(ownerid, invtype, blueprint):
    try:
        me = BlueprintOriginal.objects.get(
            ownerid=ownerid,
            blueprint=blueprint.blueprintType).me
    except BlueprintOriginal.DoesNotExist:
        tl = invtype.attribute('techLevel')
        if tl == 1:
            me = 0
        elif tl == 2:
            me = -4 # FIXME! DECRYPTOR_ME_MODIFIER
        elif tl == 3:
            me = 0
        elif tl == 0:
            me = 0
    base = Basket()
    for mat in invtype.typematerial_set.all():
        base[mat.materialType] = mat.quantity
    extra = Basket()
    for req in blueprint.blueprintType.typerequirement_set.filter(
        activity__activityName='Manufacturing'):
        if req.recycle > 0:
            for mat in req.requiredType.typematerial_set.all():
                if mat.quantity > base[mat.materialType]:
                    del base[mat.materialType]
                else:
                    base[mat.materialType] -= mat.quantity
        if req.damagePerJob > 0:
            extra[req.requiredType] = req.quantity * req.damagePerJob
    bwf = blueprint.wasteFactor
    if me >= 0:
        wf = (bwf * 0.01) * (1.0 / (1 + me))
    else:
        wf = (bwf * 0.01) * (1 - me)
    for mat, qty in base.items():
        base[mat] += int(round(qty * wf))
    basket = base + extra
    basket[blueprint.blueprintType] = 1
    basket *= 1/float(invtype.portionsize)
    basket.note = 'Blueprint'
    return basket

def build_from_reaction(ownerid, invtype):
    result = Basket(note='Reaction')
    reaction = None
    for reaction in invtype.reactedBy_set.all():
        reaction = reaction.reactionType
        if reaction.typereaction_set.filter(type=invtype,
                                            isinput=1).count() > 0:
            reaction = None
            continue
    if reaction is None:
        return None
    quantity = 1.0
    for inout in reaction.typereaction_set.all():
        if inout.isinput:
            result[inout.type] = inout.quantity * inout.type.attribute(
                'moonMiningAmount')
        else:
            quantity = inout.quantity * inout.type.attribute(
                'moonMiningAmount')
    return result * (1/float(quantity))

class Decryptor(object):
    def __init__(self, chance=1.0, runs=0, me=0, pe=0, typenames=None):
        self.chance = chance
        self.runs = runs
        self.me = me
        self.pe = pe
        self._typenames = typenames

    def typename(self, raceid):
        if self._typenames is None:
            return None
        else:
            return self._typenames[raceid]

NoDecryptor = Decryptor()
T2_DECRYPTORS = [
    NoDecryptor,
    Decryptor(chance=0.6, runs=+9, me=-2, pe=+1,
              typenames={1: 'Interface Alignment Chart',
                         2: 'Circuitry Schematics',
                         4: 'Circular Logic',
                         8: 'Symbiotic Figures'}),
    Decryptor(chance=1.0, runs=+2, me=+1, pe=+4,
              typenames={1: 'User Manual',
                         2: 'Operation Handbook',
                         4: 'Sacred Manifesto',
                         8: 'Engagement Plan'}),
    Decryptor(chance=1.1, runs=+0, me=+3, pe=+3,
              typenames={1: 'Tuning Instructions',
                         2: 'Calibration Data',
                         4: 'Formation Layout',
                         8: 'Collision Measurements'}),
    Decryptor(chance=1.2, runs=+1, me=+2, pe=+5,
              typenames={1: 'Prototype Diagram',
                         2: 'Advanced Theories',
                         4: 'Classic Doctrine',
                         8: 'Test Reports'}),
    Decryptor(chance=1.8, runs=+4, me=-1, pe=+2,
              typenames={1: 'Installation Guide',
                         2: 'Assembly Instructions',
                         4: 'War Strategon',
                         8: 'Stolen Formulas'})
    ]

ENCRYPTION_SKILL = 4
SCIENCE_SKILL = 4
META_LEVEL = 0

def invent(invtype, decryptor=NoDecryptor):
    t1type = invtype.blueprintType.productType.metatype.parentType
    product = invtype.blueprintType.productType
    if (t1type.group.groupName in ('Battlecruiser', 'Battleship') or
        product.typeName == 'Hulk'):
        chance = 0.2
    elif (t1type.group.groupName in ('Cruiser', 'Industrial') or
          product.typeName == 'Mackinaw'):
        chance = 0.25
    elif (t1type.group.groupName in ('Frigate', 'Destroyer', 'Freighter') or
          product.typeName == 'Skiff'):
        chance = 0.3
    else:
        chance = 0.4
    chance *= ((1 + 0.01 * ENCRYPTION_SKILL) *
               (1 + ((0.02 * (SCIENCE_SKILL + SCIENCE_SKILL)) *
                     (5.0 / (5 - META_LEVEL)))) *
               decryptor.chance)
    runs = min(max(int((invtype.blueprintType.maxProductionLimit / 10.0) +
                       decryptor.me),
                   1),
               invtype.blueprintType.maxProductionLimit)
    extra = t1type.producedBy.blueprintType.typerequirement_set.filter(
        activity__activityName='Invention')
    basket = Basket(note='Invention')
    for entry in extra:
        # Evil hack, these should have dpj = 0, but don't
        if entry.requiredType.group.groupName == 'Data Interfaces':
            continue
        if entry.damagePerJob > 0:
            basket[entry.requiredType] = entry.quantity * entry.damagePerJob
    basket *= 1/chance
    basket *= 1.0/runs
    return basket

RELICS = {
    'Strategic Cruiser': [('Intact Hull Section', 0.4, 10),
                          ('Malfunctioning Hull Section', 0.3, 10),
                          ('Wrecked Hull Section', 0.2, 3)],
    'Offensive Systems': [('Intact Weapon Subroutines', 0.4, 20),
                          ('Malfunctioning Weapon Subroutines', 0.3, 10),
                          ('Wrecked Weapon Subroutines', 0.2, 3)],
    'Defensive Systems': [('Intact Armor Nanobot', 0.4, 20),
                          ('Malfunctioning Armor Nanobot', 0.3, 10),
                          ('Wrecked Armor Nanobot', 0.2, 3)],
    'Electronic Systems': [('Intact Electromechanical Component', 0.4, 20),
                           ('Malfunctioning Electromechanical Component', 0.3, 10),
                           ('Wrecked Electromechanical Component', 0.2, 3)],
    'Engineering Systems': [('Intact Power Cores', 0.4, 20),
                            ('Malfunctioning Power Cores', 0.3, 10),
                            ('Wrecked Power Cores', 0.2, 3)],
    'Propulsion Systems': [('Intact Thruster Sections', 0.4, 20),
                           ('Malfunctioning Thruster Sections', 0.3, 10),
                           ('Wrecked Thruster Sections', 0.2, 3)]
    }

# raceid: typename
HYBRID_DECRYPTORS = {
    1: 'Caldari Hybrid Tech Decryptor',
    2: 'Minmatar Hybrid Tech Decryptor',
    4: 'Amarr Hybrid Tech Decryptor',
    8: 'Gallente Hybrid Tech Decryptor'
    }

def reverseengineer(invtype):
    product = invtype.blueprintType.productType
    types = []
    for relic, chance, runs in RELICS[product.group.groupName]:
        basket = Basket(note='Reverse Engineering')
        relic = Type.objects.get(typeName=relic)
        basket[relic] = 1
        decryptor = Type.objects.get(typeName=HYBRID_DECRYPTORS[product.raceID])
        basket[decryptor] = 1
        extra = invtype.typerequirement_set.filter(
            activity__activityName='Reverse Engineering')
        for entry in extra:
            if entry.damagePerJob > 0:
                basket[entry.requiredType] = (entry.quantity *
                                              entry.damagePerJob)
        basket *= (1.0/(chance * 1.872)) * (1.0/runs)
        types.append(basket)
    (intact, malfunctioning, wrecked) = types
    result = (wrecked + wrecked + wrecked + wrecked + malfunctioning) * 0.2
    return result

import collections

class Basket(collections.defaultdict):
    def __init__(self, *args, **kwargs):
        if 'note' in kwargs:
            self.note = kwargs.pop('note')
        else:
            self.note = None
        super(Basket, self).__init__(lambda: 0, *args, **kwargs)

    def __add__(self, other):
        b = Basket(note=self.note)
        for key in set(self.keys() + other.keys()):
            b[key] = self[key] + other[key]
        return b

    def __mul__(self, other):
        b = Basket(note=self.note)
        for key in self.keys():
            b[key] = self[key] * other
        return b

    def __repr__(self):
        return "<Basket {%s}>" % ", ".join("%r: %r" % (key, value)
                                           for (key, value) in self.items())

class AnnotatedFloat(float):
    def __new__(cls, value, note=None):
        obj = super(AnnotatedFloat, cls).__new__(cls, value)
        obj.note = note
        return obj
