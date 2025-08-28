import os
from django.core.asgi import get_asgi_application

# First, we set the DJANGO_SETTINGS_MODULE environment variable.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# Second, we call get_asgi_application() to initialize Django's settings,
# app registry, and other components. This is the critical step.
django_asgi_app = get_asgi_application()

# Now that Django is initialized, it is safe to import other modules
# that rely on its settings, like routing and consumers.
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import backend.analytics.routing

application = ProtocolTypeRouter({
    # HTTP requests will be handled by the initialized Django application.
    "http": django_asgi_app,
    
    # WebSocket requests will be handled by our routing configuration.
    "websocket": AuthMiddlewareStack(
        URLRouter(
            backend.analytics.routing.websocket_urlpatterns
        )
    ),
})