import os
import sys

path='/jbotserv/jbotserv'

if path not in sys.path:
  sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'jbotserv.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
