#!/usr/bin/env python

from wsgiref.simple_server import make_server

import emapp

# wsgiref.handlers.CGIHandler().run(app)

def main():
    httpd = make_server('192.168.42.1', 8000, emapp.emapp)
    print 'Serving on port 8000...'
    httpd.serve_forever()

if __name__ == '__main__':
    main()
