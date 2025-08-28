import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "upstox_trade.settings")

app = Celery("upstox_trade")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
