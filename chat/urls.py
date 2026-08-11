from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.inbox, name='inbox'),
    path('new/', views.new_message, name='new_message'),
    path('dm/<str:username>/', views.direct_chat, name='direct'),
    path('group/<int:group_id>/', views.group_chat, name='group'),
    path('api/unread/', views.unread_count, name='unread_count'),
    path('upload/file/', views.upload_file,name='upload_file'),
    path('upload/voice/',views.upload_voice,name='upload_voice'),
    path('upload/group/<int:group_id>/',  views.upload_group_file, name='upload_group_file'),
    path('upload/group/voice/<int:group_id>/', views.upload_group_voice, name='upload_group_voice'),
]
