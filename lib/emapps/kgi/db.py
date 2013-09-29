import cgi
import math
import config
import tempita

dbs = {}
def connect(name='db'):
    if name not in dbs:
        cfg = config.config()
	adapter = cfg.get(name, 'dbapi')
        mod = __import__(adapter)
        if cfg.has_option(name, 'dsn'):
            db = mod.connect(cfg.get(name, 'dsn'))
        else:
            db = mod.connect(**dict((name, value) for (name, value)
                                    in cfg.items(name)
                                    if name not in ('dbapi', 'dsn')))
        dbs[name] = db
        c = db.cursor()
	if adapter == 'MySQLdb':
            c.execute("SET time_zone = '+0:00'")
    return dbs[name]

def fetchbunches(c, cls=tempita.bunch):
    """
    Return an iterator of bunch objects from the last SELECT call.
    """
    fieldnames = [x[0] for x in c.description]
    result = []
    for row in c.fetchall():
        result.append(cls(**dict(zip(fieldnames, row))))
    return result

def paginate(table, pagesize=20, extra="", extra_args=(), dbname=None):
    db = connect(dbname)
    c = db.cursor()
    form = cgi.FieldStorage()
    try:
        page = max(int(form.getfirst("page", 1)),
                   1)
    except:
        page = 1
    # Insecure, but intended as such
    c.execute("SELECT COUNT(*) FROM %s %s" % (table, extra),
              extra_args)
    rowcount = c.fetchone()[0]
    totalpages = max(int(math.ceil(rowcount/float(pagesize))),
                     1)
    c.execute("SELECT * FROM %s %s LIMIT %s, %s" %
              (table, extra, (page-1)*pagesize, pagesize),
              extra_args)
    bunches = fetchbunches(c)
    return Page(items=bunches,
                pagenum=page,
                totalpages=totalpages)

class Page(object):
    def __init__(self, items, pagenum, totalpages):
        self.items = items
        self.pagenum = pagenum
        self.totalpages = totalpages

    def first(self):
        return self.pagenum == 1

    def last(self):
        return self.pagenum == self.totalpages
