from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/dm/(?P<conversation_id>\d+)/$', consumers.DirectMessageConsumer.as_asgi()),
    re_path(r'ws/group/(?P<group_id>\d+)/$', consumers.GroupChatConsumer.as_asgi()),
]
