from django.db import connection

from gradient.dbutils import get_typename, get_typeid

class InvType(object):
    def __init__(self, typeid=None, typename=None):
        self.typeid = typeid
        self.typename = typename

    def __repr__(self):
        return "<InvType %s: %r>" % (self.typeid, self.typename)

    @classmethod
    def from_typeid(cls, typeid):
        typename = get_typename(typeid)
        if typename is None:
            raise RuntimeError("typeid %s does not exist" % typeid)
        return cls(typeid=typeid, typename=typename)

    @classmethod
    def from_typename(cls, typename):
        typeid = get_typeid(typename)
        if typeid is None:
            raise RuntimeError("typename %r does not exist" % typename)
        typename = get_typename(typeid)
        return cls(typeid=typeid, typename=typename)

    def portionsize(self):
        c = connection.cursor()
        c.execute("SELECT portionsize FROM ccp.invtypes WHERE typeid = %s",
                  (self.typeid,))
        return c.fetchone()[0]

    def blueprint(self):
        c = connection.cursor()
        c.execute("SELECT blueprinttypeid "
                  "FROM ccp.invblueprinttypes "
                  "WHERE producttypeid = %s",
                  (self.typeid,))
        if c.rowcount > 0:
            return InvType.from_typeid(c.fetchone()[0])
        else:
            return None

    def product(self):
        c = connection.cursor()
        c.execute("SELECT producttypeid "
                  "FROM ccp.invblueprinttypes "
                  "WHERE blueprinttypeid = %s",
                  (self.typeid,))
        if c.rowcount > 0:
            return InvType.from_typeid(c.fetchone()[0])
        else:
            return None

    def group(self):
        c = connection.cursor()
        c.execute("SELECT g.groupname "
                  "FROM ccp.invtypes t "
                  "     INNER JOIN ccp.invgroups g "
                  "       ON t.groupid = g.groupid "
                  "WHERE t.typeid = %s",
                  (self.typeid,))
        return c.fetchone()[0]

    def category(self):
        c = connection.cursor()
        c.execute("SELECT c.categoryname "
                  "FROM ccp.invtypes t "
                  "     INNER JOIN ccp.invgroups g "
                  "       ON t.groupid = g.groupid "
                  "     INNER JOIN ccp.invcategories c "
                  "       ON g.categoryid = c.categoryid "
                  "WHERE t.typeid = %s",
                  (self.typeid,))
        return c.fetchone()[0]

    def attribute(self, attname):
        c = connection.cursor()
        c.execute("SELECT attributeid, defaultvalue "
                  "FROM ccp.dgmattributetypes "
                  "WHERE LOWER(attributename) = LOWER(%s)",
                  (attname,))
        if c.rowcount < 1:
            raise RuntimeError("Unknown attribute %r" % attname)
        attributeid, defaultvalue = c.fetchone()
        c.execute("SELECT COALESCE(valuefloat, valueint) "
                  "FROM ccp.dgmtypeattributes "
                  "WHERE attributeid = %s AND typeid = %s",
                  (attributeid, self.typeid))
        if c.rowcount == 0:
            return defaultvalue
        else:
            return c.fetchone()[0]

    def metatype_parent(self):
        c = connection.cursor()
        c.execute("SELECT parenttypeid "
                  "FROM ccp.invmetatypes "
                  "WHERE typeid = %s",
                  (self.typeid,))
        if c.rowcount > 0:
            return InvType.from_typeid(c.fetchone()[0])
        else:
            return None

    def metatype_children(self):
        c = connection.cursor()
        c.execute("SELECT typeid "
                  "FROM ccp.invmetatypes "
                  "WHERE parenttypeid = %s",
                  (self.typeid,))
        return [InvType.from_typeid(typeid) for (typeid,) in c.fetchall()]

    def maxproductionlimit(self):
        c = connection.cursor()
        c.execute("SELECT maxproductionlimit FROM ccp.invblueprinttypes "
                  "WHERE blueprinttypeid = %s",
                  (self.typeid,))
        if c.rowcount > 0:
            return c.fetchone()[0]
        else:
            raise RuntimeError("%s is not a blueprint" %
                               (self,))

    def typematerials(self):
        c = connection.cursor()
        c.execute("SELECT mt.typeid, "
                  "       mt.typename, "
                  "       m.quantity "
                  "FROM ccp.invtypematerials m "
                  "     INNER JOIN ccp.invtypes mt "
                  "       ON m.materialtypeid = mt.typeid "
                  "WHERE m.typeid = %s",
                  (self.typeid,))
        return [(InvType(typeid, typename), qty)
                for (typeid, typename, qty) in c.fetchall()]

    def typerequirements(self, activity):
        c = connection.cursor()
        c.execute("SELECT rt.typeid, "
                  "       rt.typename, "
                  "       req.quantity, "
                  "       req.damageperjob, "
                  "       req.recycle "
                  "FROM ccp.ramtyperequirements req "
                  "     INNER JOIN ccp.invtypes rt "
                  "       ON rt.typeid = req.requiredtypeid "
                  "     INNER JOIN ccp.ramactivities act "
                  "       ON act.activityid = req.activityid "
                  "WHERE req.typeid = %s "
                  "  AND LOWER(act.activityname) = LOWER(%s)",
                  (self.typeid, activity))
        return [(InvType(typeid, typename), qty, dpj, recycle)
                for (typeid, typename, qty, dpj, recycle)
                in c.fetchall()]

    def wastefactor(self):
        c = connection.cursor()
        c.execute("SELECT wastefactor "
                  "FROM ccp.invblueprinttypes "
                  "WHERE blueprinttypeid = %s",
                  (self.typeid,))
        if c.rowcount > 0:
            return c.fetchone()[0]
        else:
            return None

    def race(self):
        c = connection.cursor()
        c.execute("SELECT r.racename "
                  "FROM ccp.invtypes t "
                  "     INNER JOIN ccp.chrraces r "
                  "       ON t.raceid = r.raceid "
                  "WHERE t.typeid = %s",
                  (self.typeid,))
        if c.rowcount > 0:
            return c.fetchone()[0]
        else:
            return None

    def invent_to(self):
        """
        For a blueprint, return a list of blueprints that can be
        invented from this.
        """
        result = []
        product = self.product()
        for metatype in product.metatype_children():
            if metatype.attribute('metaLevel') == 5:
                result.append(metatype.blueprint())
        return result

    def invented_from(self):
        """
        For a blueprint, return the blueprint that this was invented
        from.
        """
        product = self.product()
        if int(product.attribute('metaLevel')) != 5:
            return None
        parent = product.metatype_parent()
        if parent is None:
            return None
        return parent.blueprint()

    def reacted_from(self):
        c = connection.cursor()
        c.execute("SELECT reactiontypeid "
                  "FROM ccp.invtypereactions "
                  "WHERE input = 0 AND typeid = %s",
                  (self.typeid,))
        if c.rowcount != 1:
            return None, None
        reactionid = c.fetchone()[0]
        c.execute("SELECT input, typeid, quantity "
                  "FROM ccp.invtypereactions "
                  "WHERE reactiontypeid = %s",
                  (reactionid,))
        output_qty = None
        inputs = []
        for is_input, typeid, quantity in c.fetchall():
            if typeid == self.typeid and not is_input:
                output_qty = quantity
                continue
            reqtype = InvType.from_typeid(typeid)
            if not is_input:
                inputs.append((reqtype, -quantity))
            else:
                inputs.append((reqtype, quantity))
        return output_qty, inputs

    def controltowerresources(self, purpose):
        c = connection.cursor()
        c.execute("SELECT resourcetypeid, quantity, minsecuritylevel, "
                  "       factionid "
                  "FROM ccp.invcontroltowerresources r "
                  "     INNER JOIN ccp.invcontroltowerresourcepurposes p "
                  "       ON r.purpose = p.purpose "
                  "WHERE r.controltowertypeid = %s "
                  "  AND p.purposetext = %s",
                  (self.typeid, purpose))
        result = []
        for typeid, qty, minseclevel, factionid in c.fetchall():
            result.append((InvType.from_typeid(typeid),
                           qty, minseclevel, factionid))
        return result

def get_decryptors(racename):
    if racename is None:
        racename = 'Minmatar'
    c = connection.cursor()
    c.execute("SELECT t.typeid, t.typename "
              "FROM ccp.invtypes t "
              "     INNER JOIN ccp.invgroups g "
              "       ON t.groupid = g.groupid "
              "     INNER JOIN ccp.invcategories c "
              "       ON g.categoryid = c.categoryid "
              "WHERE c.categoryname = 'Decryptors' "
              "  AND g.groupname = 'Decryptors - ' || %s",
              (racename,))
    result = []
    result.append(KeyValue(typename=None, chance=1.0, runs=0, me=0, pe=0))
    for (typeid, typename) in c.fetchall():
        invtype = InvType(typeid, typename)
        result.append(KeyValue(
                typename=typename,
                # sic!
                chance=float(invtype.attribute(
                        'inventionPropabilityMultiplier')),
                runs=int(invtype.attribute('inventionMaxRunModifier')),
                me=int(invtype.attribute('inventionMEModifier')),
                pe=int(invtype.attribute('inventionPEModifier'))))
    return result

class KeyValue(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
