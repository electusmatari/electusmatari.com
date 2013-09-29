import kgi
from responses import unauthorized

def require_permission(permission):
    def sentinel(func):
        def handler(environ, *args, **kwargs):
            user = environ['emapps.user']
            if not user.has_permission(permission):
                return kgi.html_response(
                    unauthorized(user, 'You are not an admin.')
                    )
            else:
                return func(environ, *args, **kwargs)
        return handler
    return sentinel

from kgi import template_function

import datetime

@template_function
def eve_time(time=None, includetime=True):
    if time is None:
        time = datetime.datetime.utcnow()
    try:
        if includetime:
            t = time.strftime("%m.%d %H:%M:%S")
        else:
            t = time.strftime("%m.%d")
        y = time.year - 1898
        return "%3i.%s" % (y, t)
    except:
        return "never"

import cgi
import tempita

@template_function
def addbr(str):
    return tempita.html(cgi.escape(str).replace("\n", "<br />").decode("utf-8").encode('ascii', 'xmlcharrefreplace'))

@template_function
def addnbsp(str):
    return tempita.html(cgi.escape(str).replace(" ", "&nbsp;").decode("utf-8").encode('ascii', 'xmlcharrefreplace'))

@template_function
def humane(obj):
    if isinstance(obj, int) or isinstance(obj, long):
        return humaneint(obj)
    elif isinstance(obj, float):
        return humanefloat(obj)
    else:
        return obj

def humanefloat(num):
    num = "%.2f" % float(num)
    return humaneint(num[:-3]) + num[-3:]

def humaneint(num):
    num = str(int(num))
    if num[0] == "-":
        sign = "-"
        num = num[1:]
    else:
        sign = ""
    triple = []
    while True:
        if len(num) > 3:
            triple = [num[-3:]] + triple
            num = num[:-3]
        else:
            triple = [num] + triple
            break
    return sign + ",".join(triple)
