from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='list'),
    path('<int:pk>/mark-read/', views.mark_as_read, name='mark_read'),
    path('<int:pk>/delete/', views.delete_notification, name='delete'),
    path('mark-all-read/', views.mark_all_as_read, name='mark_all_read'),
    path('unread-count/', views.unread_count, name='unread_count'),
]