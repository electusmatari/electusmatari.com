# Contracts application

import cgi
import kgi

from emapps.util import require_permission, humane

STATES = ["new", "in progress", "done", "pay later", "closed"]
NEXTSTATES = {"new": ["in progress"],
              "in progress": ["done", "pay later"],
              "done": ["closed", "pay later"],
              "pay later": ["closed"],
              "closed": ["new"]}

@require_permission('em')
def view_contracts(environ):
    user = environ['emapps.user']
    form = cgi.FieldStorage()
    if environ["REQUEST_METHOD"] == "POST":
        contractid = form.getfirst("contractid", None)
        newstate = form.getfirst("state", None)
        if None in (contractid, newstate):
            return kgi.template_response('market2/error.html',
                                         user=user,
                                         error='Bad form data.')
        if newstate not in STATES:
            return kgi.template_response('market2/error.html',
                                         user=user,
                                         error='Bad state.')
        contract = sql_get_contract(contractid)
        if contract.handler != user.username:
            return kgi.template_response('403.html', status='403 Forbidden',
                                         reason='This contract is not for you to modify.')
        sql_update_contract(contract.id, state=newstate)
        return kgi.redirect_response('http://www.electusmatari.com/market2/contracts/')
    creators = form.getlist('creator')
    queues = form.getlist('queue')
    handlers = form.getlist('handler')
    if len(creators) == 0 and len(handlers) == 0:
        creators = [user.username]
        handlers = [user.username]
    states = form.getlist('state')
    if len(states) == 0:
        states = STATES[:-1]
    return kgi.template_response('market2/contract_list.html',
                                 user=user,
                                 states=states,
                                 nextstates=NEXTSTATES,
                                 contracts=get_contracts(user.username,
                                                         creators,
                                                         queues,
                                                         handlers,
                                                         states))

@require_permission('em')
def view_contracts_create(environ):
    user = environ["emapps.user"]
    if environ["REQUEST_METHOD"] == "POST":
        form = cgi.FieldStorage()
        contracttext = form.getfirst("contracttext", None)
        queue = form.getfirst("queue", None)
        comment = form.getfirst("comment", "")
        comment = comment.strip()
        if comment == "":
            comment = None
        if None in (contracttext, queue):
            return kgi.redirect_response('http://www.electusmatari.com/market2/contracts/create/')
        contractid = sql_create_contract(user.username, contracttext)
        if comment is not None:
            sql_add_comment(contractid, user.username, comment)
        return kgi.redirect_response('http://www.electusmatari.com/market2/contracts/')
    return kgi.template_response('market2/contract_create.html',
                                 user=user)

@require_permission('em')
def view_contracts_single(environ, contractid):
    user = environ["emapps.user"]
    contract = sql_get_contract(contractid)
    if contract is None:
        return kgi.template_response('404.html', status='404 Not Found')
    elif not contract_owned_by(user.username, contract):
        return kgi.template_response('403.html', status='403 Forbidden',
                                     reason='This is none of your contracts.')
    elif environ["REQUEST_METHOD"] == "POST":
        form = cgi.FieldStorage()
        text = form.getfirst("comment", None)
        if text is not None:
            sql_add_comment(contractid, user.username, text)
        return kgi.redirect_response('http://www.electusmatari.com/market2/contracts/%s/'
                                     % contractid)
    else:
        comments = sql_get_comments(contractid)
        return kgi.template_response('market2/contract.html',
                                     user=user,
                                     contract=contract,
                                     comments=comments)

def contract_owned_by(username, contract):
    if (contract.creator == username
        or contract.handler == username):
        return True
    else:
        return False

def get_contracts(username, creators, queues, handlers, states):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    sql = ("SELECT * FROM market_contract "
           "WHERE ")
    orclauses = []
    args = []
    for (var, name) in [(creators, "creator"),
                        (queues, "queue"),
                        (handlers, "handler"),
                        (states, "state")]:
        if len(var) > 0:
            orclauses.append(" %s IN (%s) "
                             % (name,
                                ",".join(["%s"] * len(var))))
            args.extend(var)
    sql += " OR ".join(orclauses)
    c.execute(sql, args)
    bunches = [b for b in kgi.fetchbunches(c)
               if contract_owned_by(username, b)]
    for b in bunches:
        b.lastcomment = sql_get_lastcomment(b.id)
    return bunches

def sql_create_contract(creator, contracttext, handler=None,
                        state="new", queue=None):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("INSERT INTO market_contract (contracttext, creator, "
              "            handler, queue, state) "
              "VALUES (%s, %s, %s, %s, %s)",
              (contracttext, creator, handler, queue, state))
    return c.lastrowid

def sql_get_contract(contractid):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("SELECT * FROM market_contract "
              "WHERE id = %s "
              "LIMIT 1",
              (contractid,))
    if c.rowcount == 1:
        return kgi.fetchbunches(c)[0]
    else:
        return None

def sql_add_comment(contractid, author, text):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("INSERT INTO market_contract_comments (contract_id, "
              "            author, comment) "
              "VALUES (%s, %s, %s)",
              (contractid, author, text))

def sql_get_comments(contractid):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("SELECT * FROM market_contract_comments "
              "WHERE contract_id = %s "
              "ORDER BY created ASC",
              (contractid,))
    return kgi.fetchbunches(c)

def sql_get_lastcomment(contractid):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("SELECT * FROM market_contract_comments "
              "WHERE contract_id = %s "
              "ORDER BY created DESC "
              "LIMIT 1",
              (contractid,))
    if c.rowcount == 1:
        return kgi.fetchbunches(c)[0]
    else:
        return None

def sql_update_contract(contractid, state):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("UPDATE market_contract SET state = %s WHERE id = %s",
              (state, contractid))
