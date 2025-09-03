"""
ASGI config for upstox_trade project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from upstox_trade.interface.broker.urls import websocket_urlpatterns

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "upstox_trade.settings")
application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": URLRouter(websocket_urlpatterns),
    }
)
