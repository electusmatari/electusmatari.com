from django.db import models

class Category(models.Model):
    categoryID = models.IntegerField(db_column='categoryid', primary_key=True)
    categoryName = models.CharField(max_length=255, db_column='categoryname')
    description = models.TextField()
    iconID = models.IntegerField(db_column='iconid')
    published = models.IntegerField()

    def __unicode__(self):
        return self.categoryName

    class Meta:
        db_table = 'ccp"."invcategories'
        managed = False
        ordering = ['categoryName']

    def save(self, *args, **kwargs):
        raise RuntimeError('%s model is read-only ' %
                           self.__class__.__name__)

class Group(models.Model):
    groupID = models.IntegerField(db_column='groupid', primary_key=True)
    category = models.ForeignKey(Category, db_column='categoryid')
    categoryID = models.IntegerField(db_column='categoryid')
    groupName = models.CharField(max_length=255, db_column='groupname')
    description = models.TextField()
    iconID = models.IntegerField(db_column='iconid')
    useBasePrice = models.IntegerField(db_column='usebaseprice')
    allowManufacture = models.IntegerField(db_column='allowmanufacture')
    allowRecycler = models.IntegerField(db_column='allowrecycler')
    anchored = models.IntegerField()
    anchorable = models.IntegerField()
    fittablenOnSingleton = models.IntegerField(
        db_column='fittablenonsingleton')
    published = models.IntegerField()

    def __unicode__(self):
        return self.groupName

    class Meta:
        db_table = 'ccp"."invgroups'
        managed = False
        ordering = ['groupName']

    def save(self, *args, **kwargs):
        raise RuntimeError('%s model is read-only ' %
                           self.__class__.__name__)

class Type(models.Model):
    typeID = models.IntegerField(db_column="typeid", primary_key=True)
    group = models.ForeignKey(Group, db_column='groupid')
    groupID = models.IntegerField(db_column='groupid')
    typeName = models.CharField(max_length=255, db_column='typename')
    description = models.TextField()
    graphicID = models.IntegerField(db_column='graphicid')
    radius = models.FloatField()
    mass = models.FloatField()
    volume = models.FloatField()
    capacity = models.FloatField()
    portionsize = models.IntegerField()
    raceID = models.IntegerField(db_column='raceid')
    basePrice = models.FloatField(db_column='baseprice')
    published = models.IntegerField()
    marketGroupID = models.IntegerField(db_column='marketgroupid')
    chanceOfDuplicating = models.FloatField(db_column='chanceofduplicating')
    iconID = models.IntegerField(db_column='iconid')

    def __unicode__(self):
        return self.typeName

    def attribute(self, name):
        try:
            return self.typeattribute_set.get(
                attribute__attributeName=name
                ).value
        except TypeAttribute.DoesNotExist:
            return Attribute.objects.get(attributeName=name).defaultValue

    class Meta:
        db_table = 'ccp"."invtypes'
        managed = False
        ordering = ['typeName']

    def save(self, *args, **kwargs):
        raise RuntimeError('%s model is read-only ' %
                           self.__class__.__name__)

class BlueprintType(models.Model):
    blueprintTypeID = models.IntegerField(db_column="blueprinttypeid",
                                          primary_key=True)
    blueprintType = models.OneToOneField(Type, db_column="blueprinttypeid",
                                         related_name='blueprintType')
    parentBlueprintTypeID = models.IntegerField(
        db_column="parentblueprinttypeid", null=True)
    parentBlueprintType = models.ForeignKey(Type,
                                            db_column="parentblueprinttypeid",
                                            related_name='parentBlueprintType',
                                            null=True)
    productTypeID = models.IntegerField(db_column="producttypeid",
                                        null=True)
    productType = models.OneToOneField(Type, db_column='producttypeid',
                                       related_name='producedBy',
                                       null=True)
    productionTime = models.IntegerField(db_column="productiontime",
                                         null=True)
    techLevel = models.IntegerField(db_column="techlevel",
                                    null=True)
    researchProductivityTime = models.IntegerField(
        db_column="researchproductivitytime",
        null=True)
    researchMaterialTime = models.IntegerField(
        db_column="researchmaterialtime",
        null=True)
    researchCopyTime = models.IntegerField(db_column="researchcopytime",
                                           null=True)
    researchTechTime = models.IntegerField(db_column="researchtechtime",
                                           null=True)
    productivityModifier = models.IntegerField(
        db_column="productivitymodifier",
        null=True)
    materialModifier = models.IntegerField(db_column="materialmodifier",
                                           null=True)
    wasteFactor = models.IntegerField(db_column="wastefactor",
                                      null=True)
    maxProductionLimit = models.IntegerField(db_column="maxproductionlimit",
                                             null=True)

    def __unicode__(self):
        return self.blueprintType.typeName

    class Meta:
        db_table = 'ccp"."invblueprinttypes'
        managed = False
        ordering = ['blueprintType__typeName']

    def save(self, *args, **kwargs):
        raise RuntimeError('%s model is read-only ' %
                           self.__class__.__name__)

class Attribute(models.Model):
    attributeID = models.IntegerField(db_column='attributeid',
                                      primary_key=True)
    attributeName = models.CharField(max_length=255,
                                     db_column='attributename')
    description = models.TextField()
    iconID = models.IntegerField(db_column='iconid')
    defaultValue = models.FloatField(db_column='defaultvalue')
    published = models.IntegerField()
    displayName = models.CharField(max_length=255, db_column='displayname')
    unitID = models.IntegerField(db_column='unitid')
    stackable = models.IntegerField()
    highIsGood = models.IntegerField(db_column='highisgood')
    # dgmAttributeCategories
    categoryID = models.IntegerField(db_column='categoryid')

    def __unicode__(self):
        return self.attributeName

    class Meta:
        db_table = 'ccp"."dgmattributetypes'
        managed = False
        ordering = ['attributeName']

    def save(self, *args, **kwargs):
        raise RuntimeError('%s model is read-only ' %
                           self.__class__.__name__)

class TypeAttribute(models.Model):
    typeID = models.IntegerField(db_column='typeid',
                                 primary_key=True) # WRONG! But avoids id.
    type = models.ForeignKey(Type, db_column='typeid')
    attributeID = models.IntegerField(db_column='attributeid')
    attribute = models.OneToOneField(Attribute, db_column='attributeid')
    valueInt = models.IntegerField(db_column='valueint', null=True)
    valueFloat = models.FloatField(db_column='valuefloat', null=True)

    @property
    def value(self):
        return self.valueFloat or self.valueInt

    class Meta:
        db_table = 'ccp"."dgmtypeattributes'
        managed = False

    def save(self, *args, **kwargs):
        raise RuntimeError('%s model is read-only ' %
                           self.__class__.__name__)

class TypeMaterial(models.Model):
    typeID = models.IntegerField(db_column='typeid',
                                 primary_key=True) # WRONG! But avoids id.
    type = models.ForeignKey(Type, db_column='typeid')
    materialTypeID = models.IntegerField(db_column='materialtypeid')
    materialType = models.ForeignKey(Type, db_column='materialtypeid',
                                     related_name='mterialfor_set')
    quantity = models.IntegerField()

    class Meta:
        db_table = 'ccp"."invtypematerials'
        managed = False

    def save(self, *args, **kwargs):
        raise RuntimeError('%s model is read-only ' %
                           self.__class__.__name__)

class Activity(models.Model):
    activityID = models.IntegerField(db_column="activityid",
                                     primary_key=True)
    activityName = models.CharField(db_column="activityname",
                                    max_length=255)
    iconNo = models.CharField(db_column="iconno",
                              max_length=255)
    description = models.TextField()
    published = models.IntegerField()

    class Meta:
        db_table = 'ccp"."ramactivities'
        managed = False

    def save(self, *args, **kwargs):
        raise RuntimeError('%s model is read-only ' %
                           self.__class__.__name__)

class TypeRequirement(models.Model):
    typeID = models.IntegerField(db_column='typeid',
                                 primary_key=True) # WRONG! But avoids id.
    type = models.ForeignKey(Type, db_column='typeid')
    activityID = models.IntegerField(db_column='activityid')
    activity = models.ForeignKey(Activity, db_column='activityid')
    requiredTypeID = models.IntegerField(db_column='requiredtypeid')
    requiredType = models.ForeignKey(Type, db_column='requiredtypeid',
                                     related_name='requiredfor_set')
    quantity = models.IntegerField()
    damagePerJob = models.FloatField(db_column='damageperjob')
    recycle = models.IntegerField()

    class Meta:
        db_table = 'ccp"."ramtyperequirements'
        managed = False

    def save(self, *args, **kwargs):
        raise RuntimeError('%s model is read-only ' %
                           self.__class__.__name__)

class TypeReaction(models.Model):
    reactionTypeID = models.IntegerField(db_column='reactiontypeid',
                                         primary_key=True) # WRONG!
    reactionType = models.ForeignKey(Type, db_column='reactiontypeid')
    isinput = models.IntegerField(db_column='input')
    typeID = models.IntegerField(db_column='typeid')
    type = models.ForeignKey(Type, related_name='reactedBy_set',
                             db_column='typeid')
    quantity = models.IntegerField()

    class Meta:
        db_table = 'ccp"."invtypereactions'
        managed = False

    def save(self, *args, **kwargs):
        raise RuntimeError('%s model is read-only ' %
                           self.__class__.__name__)

class MetaGroup(models.Model):
    metaGroupID = models.IntegerField(primary_key=True,
                                      db_column='metagroupid')
    metaGroupName = models.CharField(max_length=255,
                                     db_column='metagroupname')
    description = models.TextField()
    iconID = models.IntegerField(db_column='iconid')

    class Meta:
        db_table = 'ccp"."invmetagroups'
        managed = False

    def save(self, *args, **kwargs):
        raise RuntimeError('%s model is read-only ' %
                           self.__class__.__name__)

class MetaType(models.Model):
    typeID = models.IntegerField(primary_key=True, db_column='typeid')
    type = models.OneToOneField(Type, db_column='typeid')
    parentTypeID = models.IntegerField(db_column='parenttypeid')
    parentType = models.ForeignKey(Type, db_column='parenttypeid',
                                   related_name='metatypechild_set')
    metaGroupID = models.IntegerField(db_column='metagroupid')
    metaGroup = models.ForeignKey(MetaGroup, db_column='metagroupid')

    class Meta:
        db_table = 'ccp"."invmetatypes'
        managed = False

    def save(self, *args, **kwargs):
        raise RuntimeError('%s model is read-only ' %
                           self.__class__.__name__)

class Flag(models.Model):
    flagID = models.IntegerField(db_column='flagid', primary_key=True)
    flagName = models.CharField(max_length=255, db_column='flagname',
                                null=True)
    flagText = models.CharField(max_length=255, db_column='flagtext',
                                null=True)
    orderID = models.IntegerField(db_column='orderid', null=True)

    def __unicode__(self):
        return self.flagName

    class Meta:
        db_table = 'ccp"."invflags'
        managed = False
        ordering = ['flagName']

class Faction(models.Model):
    factionID = models.IntegerField(db_column='factionid', primary_key=True)
    factionName = models.CharField(max_length=255, db_column='factionname')
    description = models.TextField()

    def __unicode__(self):
        return self.factionName

    class Meta:
        db_table = 'ccp"."chrfactions'
        managed = False
        ordering = ['factionName']

    def save(self, *args, **kwargs):
        raise RuntimeError('%s model is read-only ' %
                           self.__class__.__name__)

class Region(models.Model):
    regionID = models.IntegerField(db_column='regionid', primary_key=True)
    regionName = models.CharField(max_length=255, db_column='regionname')
    factionID = models.IntegerField(db_column='factionid', null=True)
    faction = models.ForeignKey(Faction, db_column='factionid', null=True)

    def __unicode__(self):
        return self.regionName

    class Meta:
        db_table = 'ccp"."mapregions'
        managed = False
        ordering = ['regionName']

    def save(self, *args, **kwargs):
        raise RuntimeError('%s model is read-only ' %
                           self.__class__.__name__)

class Constellation(models.Model):
    constellationID = models.IntegerField(db_column='constellationid',
                                          primary_key=True)
    constellationName = models.CharField(max_length=255,
                                         db_column='constellationname')
    regionID = models.IntegerField(db_column='regionid')
    region = models.ForeignKey(Region, db_column='regionid')
    factionID = models.IntegerField(db_column='factionid', null=True)
    faction = models.ForeignKey(Faction, db_column='factionid', null=True)

    def __unicode__(self):
        return self.constellationName

    class Meta:
        db_table = 'ccp"."mapconstellations'
        managed = False
        ordering = ['constellationName']

    def save(self, *args, **kwargs):
        raise RuntimeError('%s model is read-only ' %
                           self.__class__.__name__)

class SolarSystem(models.Model):
    solarSystemID = models.IntegerField(db_column='solarsystemid',
                                        primary_key=True)
    solarSystemName = models.CharField(max_length=255,
                                       db_column='solarsystemname')
    security = models.FloatField()
    regionID = models.IntegerField(db_column='regionid')
    region = models.ForeignKey(Region, db_column='regionid')
    constellationID = models.IntegerField(db_column='constellationid')
    constellation = models.ForeignKey(Constellation,
                                      db_column='constellationid')
    factionID = models.IntegerField(db_column='factionid', null=True)
    faction = models.ForeignKey(Faction, db_column='factionid', null=True)

    def __unicode__(self):
        return self.solarSystemName

    class Meta:
        db_table = 'ccp"."mapsolarsystems'
        managed = False
        ordering = ['solarSystemName']

    def save(self, *args, **kwargs):
        raise RuntimeError('%s model is read-only ' %
                           self.__class__.__name__)

class Station(models.Model):
    stationID = models.IntegerField(db_column='stationid', primary_key=True)
    stationType = models.ForeignKey(Type, db_column='stationtypeid')
    stationTypeID = models.IntegerField(db_column='stationtypeid')
    corporationID = models.IntegerField(db_column='corporationid')
    solarSystemID = models.IntegerField(db_column='solarsystemid')
    solarSystem = models.ForeignKey(SolarSystem, db_column='solarsystemid')
    stationName = models.CharField(max_length=255, db_column='stationname')

    def __unicode__(self):
        return self.stationName

    class Meta:
        db_table = 'ccp"."stastations'
        managed = False
        ordering = ['stationName']

    def save(self, *args, **kwargs):
        raise RuntimeError('%s model is read-only ' %
                           self.__class__.__name__)
