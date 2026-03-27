import os
from celery import Celery

# set default Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myfarmer.settings")

app = Celery("myfarmer")

# read settings from Django settings.py
app.config_from_object("django.conf:settings", namespace="CELERY")

# auto-discover tasks.py in apps
app.autodiscover_tasks()
