#!/usr/bin/env python

import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'gradient.settings'
sys.path.append("/home/forcer/Projects/evecode/web/gradient.electusmatari.com/data/python/")

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
