# Image gallery

import cgi
import os
import kgi

from emapps.responses import unauthorized
from emapps.util import require_permission
from emapps.util import eve_time

PUBDIR = "/gallery"
BASEDIR = "/home/forcer/Projects/emgallery"

def galleryapp(environ, start_response):
    URLCONF = [
        ('^/rc/', view_recentcomments),
        ('^/(.*)', view_gallery),
    ]
    return kgi.dispatch(environ, start_response, URLCONF)

@require_permission('em')
def view_recentcomments(environ):
    user = environ['emapps.user']
    return kgi.template_response('gallery/comments.html',
                                 user=user,
                                 current_time=eve_time(),
                                 breadcrumbs=[],
                                 comments=get_recent_comments()
                                 )

@require_permission('em')
def view_gallery(environ, path):
    user = environ['emapps.user']
    gallerydir = os.path.normpath(os.path.join(BASEDIR, path))
    breadcrumbs = make_breadcrumbs(path)
    if not gallerydir.startswith(BASEDIR):
        return kgi.html_response(
            unauthorized(user, 'File or directory does not exist.')
            )
    if os.path.isdir(gallerydir):
        if path != "" and not path.endswith("/"):
            return kgi.redirect_response('http://www.electusmatari.com/gallery/' + path + '/')
        (series, images, thumbs) = get_album(gallerydir)
        return kgi.template_response('gallery/index.html',
                                     user=user,
                                     current_time=eve_time(),
                                     breadcrumbs=breadcrumbs,
                                     series=series,
                                     images=images,
                                     thumbs=thumbs
                                     )
    elif os.path.isfile(gallerydir):
        if gallerydir.endswith(".png"):
            ct = "image/png"
        elif gallerydir.endswith(".jpg"):
            ct = "image/jpeg"
        else:
            ct = "application/binary"
        return kgi.html_response(file(gallerydir).read(),
                                 header=[('Content-Type', ct),
                                         ('Cache-Control', 'max-age=604800')])
    else:
        imagefile = None
        for ext in [".png", ".jpg"]:
            if os.path.isfile(gallerydir + ext):
                (seriesdir, imagename) = os.path.split(gallerydir)
                imagefile = imagename + ext
                if os.path.isfile(gallerydir + "_preview" + ext):
                    imagepreviewfile = imagename + "_preview" + ext
                else:
                    imagepreviewfile = imagefile
                break
        if imagefile is None:
            return kgi.template_response('404.html', status='404 Not Found')
        if environ["REQUEST_METHOD"] == 'POST':
            form = cgi.FieldStorage()
            comment = form.getfirst("comment")
            add_comment(path, user.username, comment)
            return kgi.redirect_response('http://www.electusmatari.com/gallery/' + path)
        (series, images, thumbs) = get_album(seriesdir)
        thisindex = images.index(imagename)
        if thisindex > 0:
            prev = images[thisindex - 1]
        else:
            prev = None
        if thisindex + 1 < len(images):
            next = images[thisindex + 1]
        else:
            next = None
        return kgi.template_response('gallery/image.html',
                                     user=user,
                                     current_time=eve_time(),
                                     breadcrumbs=breadcrumbs,
                                     imagename=imagename,
                                     imagefile=imagefile,
                                     imagepreviewfile=imagepreviewfile,
                                     prev=prev,
                                     next=next,
                                     comments=get_comments(path),
                                     )

def get_album(directory):
    series = []
    images = []
    thumbs = {}
    for filename in os.listdir(directory):
        fullname = os.path.join(directory, filename)
        if os.path.isdir(fullname):
            series.append(filename)
        elif "_thumb" in fullname:
            (sansext, ext) = os.path.splitext(filename)
            thumbs[sansext.replace("_thumb", "")] = filename
        elif "_preview" in fullname:
            continue
        else:
            (sansext, ext) = os.path.splitext(filename)
            images.append(sansext)
    series.sort(lambda a, b: cmp(a.lower(), b.lower()))
    images.sort(lambda a, b: cmp(a.lower(), b.lower()))
    return series, images, thumbs

def make_breadcrumbs(path):
    """
    Return a list of tuples of (pathname, pathcomponent) values.
    """
    result = []
    remaining = path
    while len(remaining) > 0 and remaining != '/':
        (newremaining, this) = os.path.split(remaining)
        result.insert(0, (os.path.join(PUBDIR, remaining), this))
        remaining = newremaining
    return result

def get_recent_comments():
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("SELECT date, author, comment, imagename FROM gallery_comments "
              "ORDER BY date DESC LIMIT 23")
    return c.fetchall()

def get_comments(imagename):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("SELECT date, author, comment FROM gallery_comments "
              "WHERE imagename = %s "
              "ORDER BY date ASC",
              (imagename))
    return c.fetchall()

def add_comment(imagename, author, comment):
    db = kgi.connect('dbforcer')
    c = db.cursor()
    c.execute("INSERT INTO gallery_comments "
              "  (imagename, author, comment) "
              "VALUES (%s, %s, %s)",
              (imagename, author, comment))

# CREATE TABLE gallery_comments (
#         id INT AUTO_INCREMENT PRIMARY KEY,
#         date TIMESTAMP DEFAULT NOW(),
#         imagename VARCHAR(255),
#         author VARCHAR(255),
#         comment TEXT
# );
