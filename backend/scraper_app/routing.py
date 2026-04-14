from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/scrape/(?P<job_id>[^/]+)/$', consumers.ScrapeProgressConsumer.as_asgi()),
]
