from django.urls import re_path
from api import consumers

websocket_urlpatterns = [
    re_path(r"ws/material/(?P<material_id>[^/]+)/$", consumers.MaterialChatConsumer.as_asgi()),
    re_path(r"ws/direct/(?P<other_user_id>\d+)/$", consumers.DirectChatConsumer.as_asgi()),
]
