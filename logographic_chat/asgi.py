"""
ASGI config for logographic_chat project.
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "logographic_chat.settings")

# Import Django's ASGI application first
django_asgi = get_asgi_application()

# Import websocket patterns after Django is set up
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

from chat.routing import websocket_urlpatterns
from chat.middleware import JWTAuthMiddleware

application = ProtocolTypeRouter({
    "http": django_asgi,
    "websocket": JWTAuthMiddleware(URLRouter(websocket_urlpatterns))
})
