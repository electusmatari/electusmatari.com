import datetime
import StringIO

from django.http import HttpResponseRedirect, Http404
from django.views.generic.simple import direct_to_template

from emtools.ccpeve.models import apiroot, APIKey
from gradient.recruitment.mybbutils import MyBB

APPLICANT_FORUM = 129

def apply_view(request):
    if (not request.user.is_authenticated() or
        request.user.profile.characterid is None):
        return direct_to_template(request, 'recruitment/need-forum-auth.html')
    try:
        applicant = Applicant.from_request(request)
    except Exception as e:
        return direct_to_template(request, 'recruitment/api-error.html',
                                  extra_context={'error': str(e)})
    mybb = MyBB()
    if (applicant.has_applied and
        mybb.get_tid(APPLICANT_FORUM,
                     applicant.charinfo.characterName) is not None):
        if request.method == 'POST':
            applicant.has_applied = False
            applicant.save(request)
            return HttpResponseRedirect('/recruitment/apply/')
        return direct_to_template(request, 'recruitment/already-applied.html',
                                  extra_context={'applicant': applicant})
    else:
        return direct_to_template(request, 'recruitment/apply.html',
                                  extra_context={'applicant': applicant})

def questionnaire(request, page):
    if (not request.user.is_authenticated() or
        request.user.profile.characterid is None):
        return direct_to_template(request, 'recruitment/need-forum-auth.html')
    try:
        applicant = Applicant.from_request(request)
    except Exception as e:
        return direct_to_template(request, 'recruitment/api-error.html',
                                  extra_context={'error': str(e)})
    pagenum = int(page)
    if pagenum > len(QUESTIONNAIRE):
        raise Http404
    if pagenum == len(QUESTIONNAIRE):
        last_page = True
    else:
        last_page = False
    page = QUESTIONNAIRE[pagenum - 1].with_applicant(applicant)
    if request.method == 'POST':
        return questionnaire_post(request, applicant, pagenum, page)
    return direct_to_template(request, 'recruitment/questionnaire.html',
                              extra_context={'applicant': applicant,
                                             'questionnaire': QUESTIONNAIRE,
                                             'page': page,
                                             'last_page': last_page})

def questionnaire_post(request, applicant, pagenum, page):
    for q in page.questions:
        answer = request.POST.get(q.name)
        applicant.answers[q.name] = answer
    applicant.save(request)
    if pagenum == len(QUESTIONNAIRE):
        post = make_forum_post(applicant)
        mybb = MyBB()
        tid = mybb.get_tid(APPLICANT_FORUM,
                           applicant.charinfo.characterName)
        mybb.create_post(APPLICANT_FORUM, "Application Form",
                         applicant.charinfo.characterName,
                         post, tid=tid)
        applicant.has_applied = True
        applicant.save(request)
        return HttpResponseRedirect('/recruitment/apply/')
    else:
        return HttpResponseRedirect('/recruitment/apply/%s/' %
                                    (pagenum + 1))


class Page(object):
    def __init__(self, title, *questions):
        self.title = title
        self.questions = questions

    def with_applicant(self, applicant):
        p = Page(self.title)
        p.questions = []
        for q in self.questions:
            q2 = q.with_applicant(applicant)
            if q2 is not None:
                p.questions.append(q2)
        return p

class CorpHistoryPage(Page):
    def with_applicant(self, applicant):
        p = Page(self.title)
        p.questions = []
        p.questions.append(Question('left-last-corp',
                                    "Why did you <b>leave your last "
                                    "corporation?</b>"))
        try:
            standings = get_standings()
        except:
            return p
        for corp in applicant.charinfo.employmentHistory:
            if standings.get(corp.corporationID, 0) < 0:
                name = get_charname(corp.corporationID)
                if name is None:
                    continue
                p.questions.append(
                    Question(
                        'corp-standing-%s' % corp.corporationID,
                        "You were a <b>member of the corporation "
                        "%s.</b> The corp or its alliance does have "
                        "negative standings with us for crimes. Could "
                        "you say a few words about this corp and why "
                        "you were a member?"
                        % name))
        return p

def get_standings():
    alliance_corps = {}
    standings = {}
    api = apiroot()
    for ally in api.eve.AllianceList().alliances:
        alliance_corps[ally.allianceID] = set()
        for corp in ally.memberCorporations:
            alliance_corps[ally.allianceID].add(corp.corporationID)
    grd = APIKey.objects.get(name='Gradient').corp()
    try:
        gcl = grd.ContactList()
    except:
        return standings
    for contact in gcl.allianceContactList:
        standings[contact.contactID] = "%+i" % contact.standing
        for corpid in alliance_corps.get(contact.contactID, []):
            standings[corpid] = "%+i" % contact.standing
    return standings

class Question(object):
    def __init__(self, name, text):
        self.name = name
        self.text = text

    def with_applicant(self, applicant):
        return self

class RaceQuestion(object):
    def __init__(self, name, **race_dict):
        self.name = name
        self.race_dict = race_dict
        self.text = None

    def with_applicant(self, applicant):
        return Question(self.name,
                        self.race_dict[applicant.charinfo.race])

class NegativeSecStatusQuestion(Question):
    def with_applicant(self, applicant):
        if applicant.charinfo.securityStatus < 0:
            return self
        else:
            return Question(None, self.text)

QUESTIONNAIRE = [
    Page('Gradient',
         Question('hear-about-grd',
                  "First of all, may I ask <b>how you did hear about "
                  "Gradient?</b>"),
         Question('why-grd',
                  "And <b>why did you choose Gradient?</b> We'd like to know "
                  "a bit about why you chose a corporation loyal to the "
                  "Republic, as opposed to other Minmatar, anti-slaver or "
                  "anti-pirate corporations."),
         Question('expectations',
                  "What do you <b>expect of Gradient</b> when you join? What "
                  "would you want to happen, what should the corporation "
                  "provide to make you feel you made the right choice?"),
         Question('why-hire',
                  "And from the other side of the coin&mdash;can you give "
                  "us a <b>reason why we do want to hire you?</b>"),
         ),
    Page('About Yourself',
         Question('interests',
                  "Thank you for your answers. Next, let's talk a bit "
                  "about yourself. What are <b>your interests</b> in "
                  "your life? What drives you, what do you do?"),
         Question('do-in-grd',
                  "Having talked about your interests, what is it that "
                  "you would like to <b>do in Gradient?</b> What "
                  "activities are you looking forward to doing here?"),
         Question('war-experience',
                  "As you know, we are regularly at war with other "
                  "capsuleer organizations. Do you have <b>experience with "
                  "being at war?</b> What is your opinion about being "
                  "regularly at war?"),
         RaceQuestion('racial-prejudices',
                      Minmatar=("We do <b>employ Caldari and Gallente,</b> "
                                "as well as clanless Minmatar. Is this a "
                                "problem for you?"),
                      Gallente=("We do <b>employ Caldari</b> pilots as long "
                                "as they are not working actively for the "
                                "State. As a Gallente, is this a problem for "
                                "you?"),
                      Caldari=("We do <b>employ Gallente pilots,</b> and "
                               "as the State is cooperating with the Amarrian "
                               "Empire, there might be a time when we are "
                               "forced to fight them actively. As a Caldari, "
                               "is this a problem for you?"),
                      Amarr=("We do not employ people like you. Why are you "
                             "here, anyway?")
                      ),
         NegativeSecStatusQuestion('negative-sec-status',
                                   "You have a <b>negative security "
                                   "status.</b> How come?"),
         ),
    CorpHistoryPage('Employment History'),
    Page('(( OOC ))',
         Question('ooc-alts',
                  "((<br />"
                  "A quick out-of-character section. Gradient is "
                  "first and foremost a roleplaying corporation. All our "
                  "channels are in-character, and we assume that you join "
                  "us because you enjoy such an environment.<br /><br /> "
                  "We are also a corporation of adults. RL &gt; EVE "
                  "is important to us. We respect Real-Life commitments, and "
                  "expect you to do likewise.<br /><br />"
                  "Finally, we are all mature. We find homophobic, racist, "
                  "sexist, and similar language boring and childish, and "
                  "tend to have not a lot of patience with that. That is, "
                  "we kick people for that if they don't grow up fast. This "
                  "includes rape metaphors.<br /><br />"
                  "That said, innuendo and \"strong\" language is generally "
                  "fine as long as it does not get out of hand.<br /><br />"
                  "As the only OOC question, <b>do you have any alts?</b>"
                  "<br />))"
                  )
         ),
    Page('Final Questions',
         Question('references',
                  "Do you know <b>anyone we could ask about you?</b> For "
                  "example, a former corp mate or similar?"),
         Question('shift',
                  "What <b>times are you usually active</b> on? We separate "
                  "the day into three <em>shifts</em>:"
                  "<ul><li>1st Shift: 06:00 - 14:00</li>"
                  "<li>2nd Shift: 14:00 - 22:00</li>"
                  "<li>3rd Shift: 22:00 - 06:00</li></ul>"
                  "Which shift would you be? This does not have to be exact, "
                  "just the best fit."),
         )
    ]

class Applicant(object):
    SESSIONVAR = 'grd-application-applicant'

    def __init__(self):
        self.charinfo = None
        self.answers = {}
        self.has_applied = False

    @classmethod
    def from_request(cls, request):
        if cls.SESSIONVAR in request.session:
            return request.session[cls.SESSIONVAR]
        else:
            applicant = cls()
            charid = request.user.profile.characterid
            api = apiroot()
            applicant.charinfo = api.eve.CharacterInfo(characterID=charid)
            request.session[cls.SESSIONVAR] = applicant
            request.session.set_expiry(60 * 60 * 24 * 365)
            return applicant

    def save(self, request):
        request.session[self.SESSIONVAR] = self
        request.session.modified = True

    def address(self):
        # Character info doesn't include sex, so no Mr. / Ms. :-(
        return self.charinfo.characterName

def get_charname(charid):
    api = apiroot()
    try:
        return api.eve.CharacterName(ids=charid).characters[0].name
    except:
        return None

def make_forum_post(applicant):
    s = StringIO.StringIO()
    s.write("Application from [b]%s[/b] (%s, %s), security status %.2f.\n" %
            (applicant.charinfo.characterName,
             applicant.charinfo.race,
             applicant.charinfo.bloodline,
             applicant.charinfo.securityStatus))
    s.write("\n")
    s.write("[size=large][b]Employment History[/b][/size]\n")
    s.write("\n")
    try:
        standings = get_standings()
    except:
        standings = None

    for corp in applicant.charinfo.employmentHistory:
        name = get_charname(corp.corporationID)
        if name is None:
            name = "(unknown name, API error)"
        ts = datetime.datetime.utcfromtimestamp(corp.startDate)
        if standings is None:
            s.write("%s %s\n" % (ts.strftime("%Y-%m-%d %H:%M:%S"),
                                 name))
        else:
            s.write("%s %s (%s)\n" %
                    (ts.strftime("%Y-%m-%d %H:%M:%S"),
                     name,
                     standings.get(corp.corporationID, 'neutral')))
    s.write("\n")
    s.write("[size=large][b]Further Information[/b][/size]\n")
    s.write("[url=https://gate.eveonline.com/Profile/%s]EVE Gate[/url]\n"
            % applicant.charinfo.characterName)
    s.write("[url=http://eve-search.com/search/author/%s]EVE Search[/url]\n"
            % applicant.charinfo.characterName)
    s.write("[url=http://eve-kill.net/?a=pilot_detail&plt_external_id=%s]"
            "EVE Kill[/url]\n" % applicant.charinfo.characterID)
    s.write("[url=http://eve.battleclinic.com/killboard/combat_record.php?"
            "type=player&name=%s]Battleclinic[/url]\n"
            % applicant.charinfo.characterName)
    s.write("\n")
    s.write("[size=large][b]Questionnaire[/b][/size]\n")
    s.write("\n")
    for page in QUESTIONNAIRE:
        page = page.with_applicant(applicant)
        s.write("[b]%s[/b]\n" % page.title)
        s.write("\n")
        for q in page.questions:
            if q.name:
                s.write("Q: %s\n" % fix_formatting(q.text))
                s.write("[quote]%s[/quote]\n\n" %
                        applicant.answers.get(q.name, ""))
    s.seek(0)
    return s.read()

def fix_formatting(s):
    return s.replace(
        "<br />", "\n"
        ).replace(
        "<b>", "[b]"
        ).replace(
            "</b>", "[/b]"
            ).replace(
            "<em>", "[i]"
            ).replace(
            "</em>", "[/i]"
            ).replace(
            "&gt;", ">"
            ).replace(
                "<ul>", "[list]"
                ).replace(
                "</ul>", "[/list]"
                ).replace(
                    "<li>", "[*]"
                    ).replace(
                    "</li>", ""
                    ).replace(
                        "&mdash;", "-"
                        )
