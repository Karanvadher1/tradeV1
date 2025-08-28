from django.core.management.base import BaseCommand
from test import run_ws_thread

class Command(BaseCommand):
    help = "Start WebSocket client"

    def handle(self, *args, **kwargs):
        run_ws_thread()
