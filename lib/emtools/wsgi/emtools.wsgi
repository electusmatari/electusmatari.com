#!/usr/bin/env python

import os

os.environ['DJANGO_SETTINGS_MODULE'] = 'emtools.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
