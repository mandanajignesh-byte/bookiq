import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import scraper_app.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookiq_project.settings')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(scraper_app.routing.websocket_urlpatterns)
    ),
})
