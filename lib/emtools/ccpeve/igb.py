from django.utils.safestring import mark_safe
from django.utils.html import escape

class IGB(object):
    def __init__(self, request):
        self.request = request

    def __nonzero__(self):
        "Return True iff this is viewed in the in-game browser."
        return 'EVE-IGB' in self.request.META.get('HTTP_USER_AGENT', '')

    @property
    def trusted(self):
        "Return True iff the in-game browser trusts this page."
        return 'yes' == self.request.META.get('HTTP_EVE_TRUSTED', 'No').lower()

class Button(object):
    def __init__(self, jscode, buttontext):
        self.jscode = jscode
        self.buttontext = buttontext

    def __unicode__(self):
        return mark_safe('<button type="button" class="igb" onclick="%s">%s</button>' %
                         (escape(self.jscode), escape(self.buttontext)))

class JoinChannel(Button):
    def __init__(self, channelname, buttontext=None):
        if buttontext is None:
            buttontext = "Join %s" % channelname
        super(JoinChannel, self).__init__('CCPEVE.joinChannel("%s")' %
                                          channelname,
                                          buttontext)

class RequestTrust(Button):
    def __init__(self, address, buttontext=None):
        if buttontext is None:
            buttontext = "Trust This Site"
        super(RequestTrust, self).__init__('CCPEVE.requestTrust("%s")' % 
                                           address,
                                           buttontext)

class ShowInfo(object):
    def __init__(self, typeid, itemid=None):
        self.typeid = typeid
        self.itemid = itemid
        if itemid is None:
            self.jscode = "CCPEVE.showInfo(%s)" % (typeid,)
        else:
            self.jscode = "CCPEVE.showInfo(%s, %s)" % (typeid, itemid)

    def __unicode__(self):
        return mark_safe('<input type="image" class="showinfo igb" '
                         'src="/media/img/icons/showinfo.png" '
                         'alt="[showinfo]" '
                         'onclick="%s" />' % escape(self.jscode))

TYPEID_CORP = 2
TYPEID_REGION = 3
TYPEID_SYSTEM = 5
TYPEID_ALLIANCE = 16159
TYPEID_CHARACTER = 1377
TYPEID_STATION = 3867

class ShowInfoCorp(ShowInfo):
    def __init__(self, corpid):
        super(ShowInfoCorp, self).__init__(TYPEID_CORP, corpid)

class ShowInfoRegion(ShowInfo):
    def __init__(self, regionid):
        super(ShowInfoRegion, self).__init__(TYPEID_REGION, regionid)

class ShowInfoSystem(ShowInfo):
    def __init__(self, systemid):
        super(ShowInfoSystem, self).__init__(TYPEID_SYSTEM, systemid)

class ShowInfoAlliance(ShowInfo):
    def __init__(self, allianceid):
        super(ShowInfoAlliance, self).__init__(TYPEID_ALLIANCE, allianceid)

class ShowInfoCharacter(ShowInfo):
    def __init__(self, characterid):
        super(ShowInfoCharacter, self).__init__(TYPEID_CHARACTER, characterid)

class ShowInfoStation(ShowInfo):
    def __init__(self, stationid):
        super(ShowInfoStation, self).__init__(TYPEID_STATION, stationid)
