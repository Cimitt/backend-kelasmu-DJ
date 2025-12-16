from django.urls import re_path
from api import consumers

# websocket url patterns untuk semua app
websocket_urlpatterns = [
    # dm chat: /ws/direct/<other_user_id>/
    re_path(r"ws/direct/(?P<other_user_id>\d+)/$", consumers.DirectChatConsumer.as_asgi()),

    # materi chat: /ws/material/<material_id>/
    re_path(r"ws/material/(?P<material_id>[^/]+)/$", consumers.MaterialChatConsumer.as_asgi()),
]
