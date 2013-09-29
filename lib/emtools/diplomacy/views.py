from emtools.utils import connect

DIPLO_FORUM = 19
PREFIX_NEED_ATTENTION = 4
PREFIX_SET_STANDING = 5
PREFIX_IN_ACTION = 8

def add_diplo_status(request, status):
    if request.user.is_anonymous():
        return
    if ('Diplomats' not in request.user.profile.mybb_groups and
        'Council' not in request.user.profile.mybb_groups):
        return

    conn = connect('emforum')
    c = conn.cursor()
    c.execute("""
SELECT t.prefix, COUNT(*)
FROM mybb_threads AS t
     LEFT JOIN mybb_posts AS p
       ON t.firstpost = p.pid
     LEFT JOIN mybb_users AS eu
       ON (CASE p.edituid WHEN 0 THEN p.uid ELSE p.edituid END) = eu.uid
WHERE t.fid = %s
 AND (t.prefix IN (%s, %s)
      OR (t.prefix = %s
          AND eu.uid = %s))
GROUP BY t.prefix
""", (DIPLO_FORUM,
      PREFIX_NEED_ATTENTION,
      PREFIX_SET_STANDING,
      PREFIX_IN_ACTION,
      request.user.profile.mybb_uid
      ))
    prefix_counts = dict(c.fetchall())
    numopen = prefix_counts.get(PREFIX_NEED_ATTENTION, 0)
    numassigned = prefix_counts.get(PREFIX_IN_ACTION, 0)
    numset = prefix_counts.get(PREFIX_SET_STANDING, 0)
    if 'Diplomats' in request.user.profile.mybb_groups:
        if numopen > 0 or numassigned > 0:
            status.append({'text': '%i open diplomatic file%s' %
                           (numopen, "s" if numopen != 1 else ""),
                           'url': 'http://www.electusmatari.com/standings/check/'})
            status.append({'text': '%i assigned to you' %
                           (numassigned,),
                           'url': 'http://www.electusmatari.com/standings/check/'})
    if 'Council' in request.user.profile.mybb_groups:
        if numset > 0:
            status.append({'text': '%i standing%s to be set' %
                           (numset, "s" if numset != 1 else ""),
                           'url': 'http://www.electusmatari.com/standings/check/'})
