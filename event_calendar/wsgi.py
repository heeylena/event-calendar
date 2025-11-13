"""
WSGI config for event_calendar project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'event_calendar.settings')

application = get_wsgi_application()
