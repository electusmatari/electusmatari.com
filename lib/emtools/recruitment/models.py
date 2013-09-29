import datetime

from django.db import models
from django.db import connection

class User(models.Model):
    userid = models.BigIntegerField()
    submitted = models.DateTimeField(auto_now_add=True)
    visibility = models.CharField(max_length=255, null=True)

    def charnames(self):
        return ", ".join(char.name for char in self.character_set.all())

    class Meta:
        ordering = ["-submitted"]

class Character(models.Model):
    user = models.ForeignKey(User)
    characterid = models.BigIntegerField()
    name = models.CharField(max_length=255)
    gender = models.CharField(max_length=32)
    race = models.CharField(max_length=255)
    bloodline = models.CharField(max_length=255)
    security = models.FloatField()
    graduation = models.DateTimeField()
    skillpoints = models.IntegerField()
    wallet = models.FloatField()
    corpid = models.BigIntegerField()
    corpname = models.CharField(max_length=255)
    corpjoin = models.DateTimeField()
    allianceid = models.BigIntegerField(null=True, default=None)
    alliancename = models.CharField(max_length=255, null=True, default=None)
    alliancejoin = models.DateTimeField(null=True, default=None)

    @property
    def sppm(self):
        age = datetime.datetime.utcnow() - self.graduation
        minutes = age.days * 24 * 60 + (age.seconds / 60)
        return self.skillpoints / float(minutes)

    def skillgroups(self):
        c = connection.cursor()
        c.execute("SELECT g.groupname, SUM(s.skillpoints) AS SP "
                  "FROM recruitment_skill s "
                  "     INNER JOIN ccp.invtypes t ON s.typeid = t.typeid "
                  "     INNER JOIN ccp.invgroups g ON t.groupid = g.groupid "
                  "WHERE s.character_id = %s "
                  "GROUP BY g.groupname "
                  "ORDER BY SP DESC", (self.id,))
        return c.fetchall()

    class Meta:
        ordering = ["name"]

class Skill(models.Model):
    character = models.ForeignKey(Character)
    typeid = models.BigIntegerField()
    typename = models.CharField(max_length=255)
    skillpoints = models.IntegerField()
    level = models.IntegerField()
    published = models.BooleanField()

    class Meta:
        ordering = ["-level", "skillpoints", "typename"]

class Implant(models.Model):
    character = models.ForeignKey(Character)
    attribute = models.CharField(max_length=255)
    augmentor = models.CharField(max_length=255)
    value = models.IntegerField()

    class Meta:
        ordering = ["attribute"]

class Standing(models.Model):
    character = models.ForeignKey(Character)
    entitytype = models.CharField(max_length=32)
    fromid = models.BigIntegerField()
    fromname = models.CharField(max_length=255)
    standing = models.FloatField()

    def expandedname(self):
        if self.entitytype == 'faction':
            return self.fromname
        elif self.entitytype == 'corp':
            c = connection.cursor()
            c.execute("SELECT f.factionname "
                      "FROM ccp.crpnpccorporations c "
                      "     INNER JOIN ccp.chrfactions f "
                      "       ON c.factionid = f.factionid "
                      "WHERE c.corporationid = %s",
                      (self.fromid,))
            if c.rowcount == 0:
                return self.fromname
            else:
                return "%s, %s" % (self.fromname, c.fetchone()[0])
        else:
            c = connection.cursor()
            c.execute("SELECT an.itemname, d.divisionname, "
                      "       f.factionname, a.level "
                      "FROM ccp.agtagents a "
                      "     INNER JOIN ccp.invnames an "
                      "       ON a.agentid = an.itemid "
                      "     INNER JOIN ccp.crpnpcdivisions d "
                      "       ON a.divisionid = d.divisionid "
                      "     INNER JOIN ccp.crpnpccorporations c "
                      "       ON a.corporationid = c.corporationid "
                      "     INNER JOIN ccp.chrfactions f "
                      "       ON c.factionid = f.factionid "
                      "WHERE a.agentid = %s", (self.fromid,))
            if c.rowcount == 0:
                return self.fromname
            else:
                (agentname, divisionname, factionname, level) = c.fetchone()
                return "%s (L%s %s for the %s)" % (self.fromname,
                                                   level,
                                                   divisionname,
                                                   factionname)

    class Meta:
        ordering = ["-entitytype", "-standing", "fromname"]
