#!/usr/bin/env python

import cgitb ; cgitb.enable()

import wsgiref
import wsgiref.handlers
import emapps

class CGIErrorHandler(wsgiref.handlers.CGIHandler):
    def log_exception(self,exc_info):
        try:
            import sys
            from traceback import print_exception
            print "Content-Type: text/plain"
            print
            print_exception(
                exc_info[0], exc_info[1], exc_info[2],
                self.traceback_limit, sys.stdout
            )
        finally:
            exc_info = None

# wsgiref.handlers.CGIHandler().run(errors(emapps.emapps))
CGIErrorHandler().run(emapps.emapps)
