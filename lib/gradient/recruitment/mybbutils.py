# Simple utility functions

import time

import MySQLdb

from django.conf import settings

def connect(dbname):
    db = MySQLdb.connect(db=dbname, user='emcom',
                         passwd=settings.MYSQL_PASSWD)
    db.set_character_set('utf8')
    return db

class MyBB(object):
    def __init__(self):
        self.conn = connect('emforum')

    def get_tid(self, fid, subject):
        c = self.conn.cursor()
        c.execute("""
SELECT tid
FROM mybb_threads
WHERE fid = %s
  AND TRIM(LOWER(subject)) = TRIM(LOWER(%s))
""", (fid, subject))
        if c.rowcount == 0:
            return None
        else:
            return c.fetchone()[0]

    def create_post(self, fid, username, subject, message, tid=None, uid=0,
                    dateline=None, ipaddress=None, longipaddress=0, visible=1,
                    posthash=None, prefix=0):
        if dateline is None:
            dateline = int(time.time())
        if ipaddress is None:
            ipaddress = '127.0.0.1'
        if posthash is None:
            posthash = ""
        if tid is None:
            tid = self.create_thread(fid, subject, prefix, uid, username,
                                     dateline, 0, dateline,
                                     username, uid, visible)
            new_thread = True
        else:
            new_thread = False
        c = self.conn.cursor()
        c.execute("""
INSERT INTO mybb_posts (tid, fid, subject, uid, username, dateline, message,
  ipaddress, longipaddress, visible, posthash)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
""", (tid, fid, subject, uid, username, dateline, message,
      ipaddress, longipaddress, visible, posthash))
        postid = c.lastrowid
        if new_thread:
            c.execute("UPDATE mybb_threads SET firstpost = %s "
                      "WHERE tid = %s", (postid, tid))
        else:
            c.execute("UPDATE mybb_threads "
                      "SET lastpost = %s, "
                      "    replies = replies + 1 "
                      "WHERE tid = %s", (dateline, tid))
        c.execute("UPDATE mybb_forums "
                  "   SET posts = posts + 1, "
                  "       lastpost = %s, "
                  "       lastposter = %s, "
                  "       lastposteruid = %s, "
                  "       lastposttid = %s, "
                  "       lastpostsubject = %s "
                  "WHERE fid = %s",
                  (dateline, username, uid, tid, subject, fid))

    def create_thread(self, fid, subject, prefix, uid, username, dateline,
                      firstpost, lastpost, lastposter, lastposteruid, visible):
        c = self.conn.cursor()
        c.execute("""
INSERT INTO mybb_threads (fid, subject, prefix, uid, username, dateline,
  firstpost, lastpost, lastposter, lastposteruid, visible, notes)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '')
""", (fid, subject, prefix, uid, username, dateline,
      firstpost, lastpost, lastposter, lastposteruid, visible))
        tid = c.lastrowid
        c.execute("UPDATE mybb_forums SET threads = threads + 1 "
                  "WHERE fid = %s", (fid,))
        return tid
