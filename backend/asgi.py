import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

# http dj app
django_asgi_app = get_asgi_application()
from api.middleware import JWTAuthMiddleware
from backend.routing import websocket_urlpatterns


# protokol untuk http + websocket
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddleware(  # middleware jwt
        URLRouter(websocket_urlpatterns)
    ),
})
