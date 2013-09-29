# CREATE UNIQUE INDEX intel_entity_name_key
#   ON intel_entity(entitytype, LOWER(name));
# ALTER TABLE intel_kill DROP CONSTRAINT intel_kill_system_id_fkey;

import base64
import datetime
import hashlib
import pickle

from django.contrib.auth.models import User
from django.db import models, connection
from django.utils.safestring import mark_safe
from django.utils.html import escape

from emtools.ccpeve import igb
from emtools.ccpeve.models import apiroot, SolarSystem
from emtools.ccpeve import eveapi 

from emtools.ccpeve.apiutils import get_ownerid
from emtools.ccpeve.ccputils import is_valid_characterid
from emtools.ccpeve.ccputils import is_valid_corporationid, is_valid_allianceid
from emtools.ccpeve.ccputils import is_valid_factionid

##################################################################
# Factions

class FactionManager(models.Manager):
    def get_or_create_from_api(self, factionid=None, name=None):
        return generic_get_or_create_from_api(Faction, is_valid_factionid,
                                              'factionid', factionid, name)

class Faction(models.Model):
    objects = FactionManager()

    name = models.CharField(max_length=128)
    factionid = models.BigIntegerField(null=True)

    def apicheck(self):
        c = connection.cursor()
        c.execute("SELECT factionname FROM ccp.invfactions "
                  "WHERE factionid = %s" % (self.factionid,))
        if c.rowcount != 1:
            raise NotOnAPIError("No faction with id %s found" % self.factionid)
        else:
            self.name = c.fetchone()[0]

    def html(self):
        icons = {'Amarr Empire': '/media/img/icons/amarr16.png',
                 'Minmatar Republic': '/media/img/icons/minmatar16.png',
                 'Gallente Federation': '/media/img/icons/gallente16.png',
                 'Caldari State': '/media/img/icons/caldari16.png'}
        if self.name in icons:
            return mark_safe('<img src="%s" />%s</img>' %
                             (icons[self.name], self.name))
        else:
            return self.name

    def bightml(self):
        icons = {'Amarr Empire': '/media/img/icons/amarr.png',
                 'Minmatar Republic': '/media/img/icons/minmatar.png',
                 'Gallente Federation': '/media/img/icons/gallente.png',
                 'Caldari State': '/media/img/icons/caldari.png'}
        if self.name in icons:
            return mark_safe('<img src="%s" />%s</img>' %
                             (icons[self.name], self.name))
        else:
            return self.name

##################################################################
# Alliances

class AllianceManager(models.Manager):
    def get_or_create_from_api(self, allianceid=None, name=None):
        return generic_get_or_create_from_api(Alliance, is_valid_allianceid,
                                              'allianceid', allianceid, name)

class Alliance(models.Model):
    objects = AllianceManager()

    name = models.CharField(max_length=128, blank=True)
    allianceid = models.BigIntegerField(null=True)
    ticker = models.CharField(max_length=12, null=True)
    members = models.IntegerField(null=True)
    standing = models.IntegerField(null=True)

    lastseen = models.DateTimeField(auto_now=True)
    lastkillinfo = models.DateTimeField(null=True)
    lastapi = models.DateTimeField(null=True)
    lastcache = models.DateTimeField(null=True)
    do_api_check = models.BooleanField(default=False)

    def fullname(self):
        if self.ticker:
            return "%s <%s>" % (self.name, self.ticker)
        else:
            return self.name

    def apicheck(self):
        if self.allianceid is None:
            return
        api = apiroot()
        allyapi = api.eve.AllianceList()
        lastapi = datetime.datetime.utcfromtimestamp(
            allyapi._meta.currentTime)
        for allyinfo in allyapi.alliances:
            if self.allianceid == allyinfo.allianceID:
                self.update_intel(lastapi,
                                  name=allyinfo.name,
                                  ticker=allyinfo.shortName,
                                  members=allyinfo.memberCount,
                                  lastapi=lastapi,
                                  do_api_check=False)
                return
        self.update_intel(lastapi,
                          members=0,
                          lastapi=lastapi,
                          do_api_check=False)

    def __unicode__(self):
        if self.standing is not None and self.standing != 0:
            if self.standing > 5:
                color = 'darkblue'
            elif self.standing > 0:
                color = 'blue'
            elif self.standing < -5:
                color = 'red'
            elif self.standing < 0:
                color = 'orange'
            tag = mark_safe('<img src="/media/img/icons/standings/%s.png" />' %
                            (color,))
        else:
            tag = mark_safe("")
                    
        link = mark_safe('<a href="/intel/alliance/%s" class="nobreak">%s</a>' %
                         (escape(self.name), escape(self.fullname())))
        showinfo = igb.ShowInfoAlliance(self.allianceid).__unicode__()
        return mark_safe('<span class="nobreak">') + link + tag + showinfo + mark_safe('</span>')

    def update_intel(self, timestamp, **kwargs):
        for field, value in kwargs.items():
            if field == 'name':
                if newer_than(timestamp, self.lastapi, self.lastkillinfo):
                    if self.name != '' and self.name != value:
                        Change.objects.create(
                            alliance=self,
                            changetype='name',
                            oldstring=self.name,
                            newstring=value)
                    self.name = value
            elif field == 'ticker':
                if newer_than(timestamp, self.lastapi):
                    self.ticker = value
            elif field == 'members':
                if newer_than(timestamp, self.lastapi):
                    if self.members != value:
                        Change.objects.create(
                            alliance=self,
                            changetype='members',
                            oldint=self.members,
                            newint=value)
                    self.members = value
            elif field in ('lastkillinfo', 'lastapi', 'lastcache'):
                current = getattr(self, field)
                if current is None:
                    setattr(self, field, value)
                else:
                    setattr(self, field, max(current, value))
            else:
                setattr(self, field, value)
        self.save()

    class Meta:
        ordering = ["name"]

##################################################################
# Corporations

class CorporationManager(models.Manager):
    def get_or_create_from_api(self, corporationid=None, name=None):
        return generic_get_or_create_from_api(Corporation,
                                              is_valid_corporationid,
                                              'corporationid',
                                              corporationid,
                                              name)

class Corporation(models.Model):
    objects = CorporationManager()

    name = models.CharField(max_length=128, blank=True)
    corporationid = models.BigIntegerField(null=True, default=None)
    faction = models.ForeignKey(Faction, null=True, default=None)
    alliance = models.ForeignKey(Alliance, null=True, default=None)
    ticker = models.CharField(max_length=12, null=True, default=None)
    members = models.IntegerField(null=True, default=None)
    standing = models.IntegerField(null=True, default=None)

    lastseen = models.DateTimeField(auto_now=True)
    lastkillinfo = models.DateTimeField(null=True, default=None)
    lastapi = models.DateTimeField(null=True, default=None)
    lastcache = models.DateTimeField(null=True, default=None)
    do_api_check = models.BooleanField(default=False)
    do_cache_check = models.BooleanField(default=False)

    def fullname(self):
        if self.ticker:
            return "%s [%s]" % (self.name, self.ticker)
        else:
            return self.name

    def apicheck(self):
        if self.corporationid is None:
            return
        api = apiroot()
        corpinfo = api.corp.CorporationSheet(corporationID=self.corporationid)
        lastapi = datetime.datetime.utcfromtimestamp(
            corpinfo._meta.currentTime)
        if corpinfo.ceoID >= 90000000: # Not an NPC
            ceo, created = Pilot.objects.get_or_create_from_api(
                characterid=corpinfo.ceoID)
            if not created:
                ceo.apicheck()
        if hasattr(corpinfo, 'allianceID') and corpinfo.allianceID > 0:
            ally, created = Alliance.objects.get_or_create_from_api(
                allianceid=corpinfo.allianceID)
            self.update_intel(lastapi, faction=None)
        else:
            ally = None
        # Corp 1028105327 has no ticker ...
        if not isinstance(corpinfo.ticker, (basestring, int)):
            corpinfo.ticker = ''
        self.update_intel(
            lastapi,
            name=corpinfo.corporationName,
            alliance=ally,
            ticker=corpinfo.ticker,
            members=corpinfo.memberCount,
            lastapi=lastapi,
            do_api_check=False
            )

    def __unicode__(self):
        if self.standing is not None and self.standing != 0:
            if self.standing > 5:
                color = 'darkblue'
            elif self.standing > 0:
                color = 'blue'
            elif self.standing < -5:
                color = 'red'
            elif self.standing < 0:
                color = 'orange'
            tag = mark_safe('<img src="/media/img/icons/standings/%s.png" />' %
                            (color,))
        else:
            tag = mark_safe("")
        link = mark_safe('<a href="/intel/corp/%s" class="nobreak">%s</a>' %
                         (escape(self.name), escape(self.fullname())))
        showinfo = igb.ShowInfoCorp(self.corporationid).__unicode__()
        return mark_safe('<span class="nobreak">') + link + tag + showinfo + mark_safe('</span>')

    class Meta:
        ordering = ["name"]

    def update_intel(self, timestamp, **kwargs):
        for field, value in kwargs.items():
            if field == 'name':
                if newer_than(timestamp, self.lastapi, self.lastkillinfo):
                    if self.name != '' and self.name != value:
                        Change.objects.create(
                            corporation=self,
                            changetype='name',
                            oldstring=self.name,
                            newstring=value)
                    self.name = value
            elif field == 'faction':
                if newer_than(timestamp, self.lastcache, self.lastkillinfo):
                    if self.faction != value:
                        Change.objects.create(
                            corporation=self,
                            changetype='faction',
                            oldfaction=self.faction,
                            newfaction=value)
                    self.faction = value
            elif field == 'alliance':
                if newer_than(timestamp, self.lastapi):
                    if self.alliance != value:
                        Change.objects.create(
                            corporation=self,
                            changetype='alliance',
                            oldalliance=self.alliance,
                            newalliance=value)
                    self.alliance = value
            elif field == 'ticker':
                if newer_than(timestamp, self.lastapi):
                    self.ticker = value
            elif field == 'members':
                if newer_than(timestamp, self.lastapi):
                    if self.members != value:
                        Change.objects.create(
                            corporation=self,
                            changetype='members',
                            oldint=self.members,
                            newint=value)
                    self.members = value
            elif field in ('lastkillinfo', 'lastapi', 'lastcache'):
                current = getattr(self, field)
                if current is None:
                    setattr(self, field, value)
                else:
                    setattr(self, field, max(current, value))
            else:
                setattr(self, field, value)
        self.save()


##################################################################
# Pilots

class PilotManager(models.Manager):
    def get_or_create_from_api(self, characterid=None, name=None):
        return generic_get_or_create_from_api(Pilot, is_valid_characterid,
                                              'characterid',
                                              characterid, name)

class Pilot(models.Model):
    objects = PilotManager()

    name = models.CharField(max_length=128, blank=True)
    characterid = models.BigIntegerField(null=True)
    corporation = models.ForeignKey(Corporation, null=True)
    alliance = models.ForeignKey(Alliance, null=True)
    security = models.FloatField(null=True)

    evewho = models.BooleanField(default=False)

    lastseen = models.DateTimeField(auto_now=True)
    lastkillinfo = models.DateTimeField(null=True)
    lastapi = models.DateTimeField(null=True)
    lastcache = models.DateTimeField(null=True)
    do_api_check = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def apicheck(self):
        if self.characterid is None:
            return
        api = apiroot()
        charinfo = api.eve.CharacterInfo(characterID=self.characterid)
        corp, created = Corporation.objects.get_or_create(
            corporationid=charinfo.corporationID)
        if hasattr(charinfo, 'allianceID'):
            ally, created = Alliance.objects.get_or_create(
                allianceid=charinfo.allianceID)
        else:
            ally = None
        lastapi = datetime.datetime.utcfromtimestamp(
            charinfo._meta.currentTime)
        self.update_intel(
            lastapi,
            name=charinfo.characterName,
            corporation=corp,
            alliance=ally,
            security=charinfo.securityStatus,
            lastapi=lastapi,
            do_api_check=False,
            )

    def __unicode__(self):
        link = mark_safe('<a href="/intel/pilot/%s" class="nobreak">%s</a>' %
                         (escape(self.name), escape(self.name)))
        showinfo = igb.ShowInfoCharacter(self.characterid).__unicode__()
        return mark_safe('<span class="nobreak">') + link + showinfo + mark_safe('</span>')

    def update_intel(self, timestamp, **kwargs):
        for field, value in kwargs.items():
            if field == 'name':
                if newer_than(timestamp, self.lastapi, self.lastkillinfo):
                    if self.name != '' and self.name != value:
                        Change.objects.create(
                            pilot=self,
                            changetype='name',
                            oldstring=self.name,
                            newstring=value)
                    self.name = value
            elif field == 'corporation':
                if newer_than(timestamp, self.lastapi):
                    if self.alliance != value:
                        Change.objects.create(
                            pilot=self,
                            changetype='corp',
                            oldcorp=self.corporation,
                            newcorp=value)
                    self.corporation = value
            elif field == 'alliance':
                if newer_than(timestamp, self.lastkillinfo, self.lastapi):
                    self.alliance = value
            elif field == 'security':
                if newer_than(timestamp, self.lastapi):
                    self.security = value
            elif field in ('lastkillinfo', 'lastapi', 'lastcache'):
                current = getattr(self, field)
                if current is None:
                    setattr(self, field, value)
                else:
                    setattr(self, field, max(current, value))
            else:
                setattr(self, field, value)
        self.save()

##################################################################
# Other models

class TrackedEntity(models.Model):
    corporation = models.ForeignKey(Corporation, null=True)
    alliance = models.ForeignKey(Alliance, null=True)

    def __unicode__(self):
        if self.corporation is not None:
            return self.corporation.name
        if self.alliance is not None:
            return self.alliance.name
        return "<Tracked Entity %i>" % self.id

class Change(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    changetype = models.CharField(max_length=128)
    pilot = models.ForeignKey(Pilot, null=True, default=None)
    corporation = models.ForeignKey(Corporation, null=True, default=None)
    alliance = models.ForeignKey(Alliance, null=True, default=None)
    oldint = models.IntegerField(null=True, default=None)
    oldstring = models.CharField(max_length=128, blank=True, default='')
    oldcorp = models.ForeignKey(Corporation, null=True, related_name='+',
                                 default=None)
    oldalliance = models.ForeignKey(Alliance, null=True, related_name='+',
                                     default=None)
    oldfaction = models.ForeignKey(Faction, null=True, related_name='+',
                                    default=None)
    newint = models.IntegerField(null=True, default=None)
    newstring = models.CharField(max_length=128, blank=True, default='')
    newcorp = models.ForeignKey(Corporation, null=True, related_name='+',
                                 default=None)
    newalliance = models.ForeignKey(Alliance, null=True, related_name='+',
                                     default=None)
    newfaction = models.ForeignKey(Faction, null=True, related_name='+',
                                    default=None)

    def verbose(self):
        who = (self.pilot or self.corporation or self.alliance).fullname()
        if self.changetype == 'members':
            change = self.newint - self.oldint
            if change > 0:
                return "%s gained %s members" % (who, change)
            else:
                return "%s lost %s members" % (who, -change)
        elif self.changetype == 'name':
            return "%s changed name to %s" % (self.oldstring, self.newstring)
        elif self.changetype == 'corp':
            if self.oldcorp is None:
                return ("%s joined corp %s" %
                        (who, self.newcorp.fullname()))
            else:
                return ("%s changed corp from %s to %s" %
                        (who, self.oldcorp.fullname(),
                         self.newcorp.fullname()))
        elif self.changetype == 'alliance':
            if self.oldalliance is None:
                return ("%s joined alliance %s" %
                        (who, self.newalliance.fullname()))
            elif self.newalliance is None:
                return ("%s left alliance %s" %
                        (who, self.newalliance.fullname()))
            else:
                return ("%s changed alliance from %s to %s" %
                        (who, self.oldalliance.fullname(),
                         self.newalliance.fullname()))
        elif self.changetype == 'faction':
            if self.oldfaction is None:
                return ("%s joined faction %s" %
                        (who, self.newfaction.name))
            elif self.newfaction is None:
                return ("%s left faction %s" %
                        (who, self.newfaction.name))
            else:
                return ("%s changed faction from %s to %s" %
                        (who, self.oldfaction.name,
                         self.newfaction.name))

class ChangeLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    pilot = models.ForeignKey(Pilot)
    oldcorp = models.ForeignKey(Corporation, null=True,
                                related_name="changelog_old_set")
    newcorp = models.ForeignKey(Corporation, null=True,
                                related_name="changelog_new_set")
    oldalliance = models.ForeignKey(Alliance, null=True,
                                    related_name="changelog_old_set")
    newalliance = models.ForeignKey(Alliance, null=True,
                                    related_name="changelog_new_set")

    class Meta:
        ordering = ["-timestamp"]

class Trace(models.Model):
    submitted = models.DateTimeField(auto_now_add=True)
    timestamp = models.DateTimeField()
    pilot = models.ForeignKey(Pilot)
    corporation = models.ForeignKey(Corporation)
    alliance = models.ForeignKey(Alliance, null=True)
    system = models.CharField(max_length=128)
    systemid = models.IntegerField()
    # NULL means this was in space
    station = models.CharField(max_length=128, null=True)
    stationid = models.IntegerField(null=True)
    # NULL means this was from a kill mail, not from a locator agent
    agent = models.CharField(max_length=128, null=True)
    online = models.NullBooleanField()
    submitter = models.ForeignKey(User, null=True)

    class Meta:
        ordering = ["-timestamp"]

    def get_online_display(self):
        if self.online is None:
            return "Unknown"
        elif self.online is False:
            return "No"
        else:
            return "Yes"

    def get_system_display(self):
        showinfo = igb.ShowInfoSystem(self.systemid).__unicode__()
        return mark_safe(escape(self.system)) + showinfo

    def get_station_display(self):
        if self.station is None:
            return "In Space"
        else:
            showinfo = igb.ShowInfoStation(self.stationid).__unicode__()
            return mark_safe(escape(self.station)) + showinfo

##################################################################
# intel v2.0

class KillManager(models.Manager):
    def get_or_create_from_killinfo(self, ki):
        unique = ("%s %s %s" %
                  (ki.killtime.strftime("%Y-%m-%dT%H:%M:%S"),
                   ki.solarsystemid,
                   ki.moonid or ki.victim.characterid))
        hash = hashlib.sha1(unique).hexdigest()
        obj, created = Kill.objects.get_or_create(
            hash=hash,
            defaults={'timestamp': ki.killtime,
                      'system_id': ki.solarsystemid,
                      'pickle': ''})
        if created:
            obj.pickle = base64.b64encode(pickle.dumps(ki, -1))
            obj.save()
        return obj, created

class Kill(models.Model):
    objects = KillManager()

    timestamp = models.DateTimeField(db_index=True)
    system = models.ForeignKey(SolarSystem)
    hash = models.CharField(max_length=128, db_index=True, unique=True)
    pickle = models.TextField()
    original = models.TextField(null=True, blank=True, default=None)
    involvedpilots = models.ManyToManyField(Pilot)
    involvedcorps = models.ManyToManyField(Corporation)
    involvedalliances = models.ManyToManyField(Alliance)
    involvedfactions = models.ManyToManyField(Faction)
    involved_added = models.BooleanField(default=False, db_index=True)

    def __unicode__(self):
        return self.hash

    @property
    def killinfo(self):
        if not hasattr(self, "_killinfo"):
            self._killinfo = pickle.loads(base64.b64decode(self.pickle))
        return self._killinfo

    def add_involved(self, cache=None):
        if cache is None:
            cache = EntityCache()
        for p in [self.killinfo.victim] + self.killinfo.attackers:
            pilot = None
            corp = None
            alliance = None
            faction = None
            if p.charactername:
                pilot = cache.get_pilot(p.characterid, p.charactername)
                if pilot is not None:
                    self.involvedpilots.add(pilot)
            if p.corporationname:
                corp = cache.get_corp(p.corporationid, p.corporationname)
                if corp is not None:
                    self.involvedcorps.add(corp)
            if p.alliancename:
                alliance = cache.get_alliance(p.allianceid, p.alliancename)
                if alliance is not None:
                    self.involvedalliances.add(alliance)
            if p.factionname:
                faction = cache.get_faction(p.factionid, p.factionname)
                if faction is not None:
                    self.involvedfactions.add(faction)
            if pilot is not None:
                pilot.update_intel(self.killinfo.killtime,
                                   corporation=corp,
                                   alliance=alliance,
                                   lastkillinfo=self.killinfo.killtime)
            if corp is not None:
                corp.update_intel(self.killinfo.killtime,
                                  alliance=alliance)
                if faction is not None:
                    corp.update_intel(self.killinfo.killtime,
                                      faction=faction)
                corp.update_intel(self.killinfo.killtime,
                                  lastkillinfo=self.killinfo.killtime)
        self.involved_added = True
        self.save()

class EntityCache(object):
    def __init__(self):
        self.idcache = {}
        self.namecache = {}

    def get_generic(self, Model, itemid, name):
        self.idcache.setdefault(Model.__name__, {})
        idcache = self.idcache[Model.__name__]
        self.namecache.setdefault(Model.__name__, {})
        namecache = self.namecache[Model.__name__]
        if itemid == 0:
            itemid = None
        if name == "":
            name = None
        if itemid is not None and itemid in idcache:
            return idcache[itemid]
        if name is not None and name.lower() in namecache:
            return namecache[name.lower()]
        try:
            obj, created = Model.objects.get_or_create_from_api(itemid, name)
        except NotOnAPIError:
            obj = None
        except eveapi.Error as e:
            if e.code in (105, 522, 523): # char/corp ID not found
                obj = None
            else: # Rest is an actual error
                raise
        if itemid is not None:
            self.idcache[Model.__name__][itemid] = obj
        elif name is not None:
            self.namecache[Model.__name__][name] = obj
        return obj

    def get_pilot(self, itemid, name):
        return self.get_generic(Pilot, itemid, name)

    def get_corp(self, itemid, name):
        return self.get_generic(Corporation, itemid, name)

    def get_alliance(self, itemid, name):
        return self.get_generic(Alliance, itemid, name)

    def get_faction(self, itemid, name):
        return self.get_generic(Faction, itemid, name)

class Feed(models.Model):
    lastchecked = models.DateTimeField(null=True, default=None)
    feedtype = models.CharField(max_length=32)
    url = models.CharField(max_length=255)
    state = models.TextField(null=True, default=None)
    failed_attempts = models.IntegerField(default=0)
    disabled = models.BooleanField(default=False)
    error = models.CharField(max_length=255, blank=True, default="")

    def __unicode__(self):
        return self.url

class EDKFeed(models.Model):
    lastchecked = models.DateTimeField(null=True, default=None)
    corpid = models.BigIntegerField(null=True)
    allianceid = models.BigIntegerField(null=True)
    state = models.TextField(null=True, default=None)
    failed_attempts = models.IntegerField(default=0)
    error = models.CharField(max_length=255, blank=True, default="")

    @property
    def feedtype(self):
        return 'idfeed'

    @property
    def url(self):
        if self.corpid is not None:
            name = 'corp'
            itemid = self.corpid
        else:
            name = 'alliance'
            itemid = self.allianceid
        return 'http://eve-kill.net/?a=idfeed&%s=%s' % (name, itemid)

    @property
    def disabled(self):
        return False

    @disabled.setter
    def disabled(self, value):
        pass

    def __unit__(self):
        if self.corpid is not None:
            return "Corp %s" % self.corpid
        else:
            return "Alliance %s" % self.allianceid

def newer_than(checkts, *timestamps):
    for ts in timestamps:
        if ts is not None and checkts < ts:
            return False
    return True

def generic_get_or_create_from_api(Model, is_valid, idfield,
                                   itemid=None, name=None):
    if itemid is None:
        if name is None:
            raise TypeError('Pass either an itemid or a name')
        try:
            qs = Model.objects.filter(name__iexact=name)
            if Model.__class__.__name__ in ('Corporation', 'Alliance'):
                qs = qs.order_by('-members') # members=0 last
            if Model.__class__.__name__ == 'Pilot':
                qs = qs.order_by('-corporation_id') # Doomheim last
            return qs[0:1].get(), False
        except Model.DoesNotExist:
            pass
        itemid = get_ownerid(name)
        if itemid is None:
            raise NotOnAPIError("No ownerID for name %r found " %
                                (name,))
    if not is_valid(itemid):
        raise NotOnAPIError("Invalid %s: %s" % (idfield, itemid))
    obj, created = Model.objects.get_or_create(
        **{idfield: itemid})
    if created:
        try:
            obj.apicheck()
        except eveapi.Error as e:
            if e.code in (105, # Invalid characterID
                          522, # CharacterInfo with bad characterID
                          523, # CorporationSheet with bad corporationID
                          ):
                obj.delete()
                raise NotOnAPIError("API error %s: %s" % (e.code, str(e)))
            else:
                raise
    return obj, created

class NotOnAPIError(Exception):
    pass

