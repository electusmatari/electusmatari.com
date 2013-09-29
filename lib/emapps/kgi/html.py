import re
import wsgiref

from template import template

def dispatch(environ, start_response, urlconf):
    """
    Dispatch the request according to urlconf.

    urlconf should be a list of tuples with a regular expression and a
    view function. If the regular expression matches the PATH_INFO,
    the view is called with the environ and the matched items
    (positional and named matches).

    URLCONF = [
      ('/foo/(?P<foo>[0-9]+)/', view_foo),
      ('/bar/', view_bar)
    ]
    dispatch(environ, start_response, URLCONF)
    """
    for (pattern, view) in urlconf:
        rx = re.compile(pattern)
        m = rx.match(environ["PATH_INFO"])
        if m is not None:
            d = m.groupdict()
            if len(d) == 0:
                (status, headers, body) = view(environ, *m.groups())
            else:
                (status, headers, body) = view(environ, **m.groupdict())
            start_response(status, headers)
            try:
                return body.encode('utf-8')
            except:
                return body

    if not environ["PATH_INFO"].endswith("/"):
        uri = wsgiref.util.request_uri(environ, include_query=0)
        (status, headers, body) = redirect_response(uri + "/")
    else:
        uri = wsgiref.util.request_uri(environ, include_query=1)
        (status, headers, body) = view404(environ, path=uri)
    start_response(status, headers)
    try:
        return body.encode('utf-8')
    except:
        return body

def html_response(data, status='200 Ok',
                  header=[('Content-Type', 'text/html')]):
    """
    Return a standard HTML response.
    """
    return (status, header, data)

def template_response(templatename, status='200 Ok',
                      header=[('Content-Type', 'text/html')],
                      **kwargs):
    """
    Return a template as HTML.
    """
    return html_response(template(templatename, **kwargs),
                         status=status,
                         header=header)

def redirect_response(uri, status='301 Moved Permanently',
                      header=[('Content-Type', 'text/html')]):
    """
    Return a redirect request.
    """
    return (status, header + [('Location', uri)], '')

def view404(environ, path):
    """
    A 404 error.
    Use the template '404.html', or ours if it's not present.
    """
    try:
        data = template('404.html', path=environ["PATH_INFO"])
    except IOError:
        data = """\
<html>
  <head>
    <title>404 Not Found</title>
  </head>
  <body>
    <h1>404 Not Found</h1>
    <p>The resource you were trying to access does not exist.</p>
  </body>
</html>
"""
    return ('404 Not Found', [('Content-Type', 'text/html')], data)
