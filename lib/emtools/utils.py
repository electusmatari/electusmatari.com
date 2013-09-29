# Simple utility functions

import MySQLdb
from django.conf import settings

def connect(dbname):
    return MySQLdb.connect(db=dbname, user='emcom',
                           passwd=settings.MYSQL_PASSWD)
