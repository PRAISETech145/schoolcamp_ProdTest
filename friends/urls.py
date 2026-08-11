from django.urls import path
from . import views

app_name = 'friends'

urlpatterns = [
    path('', views.friends_list_view, name='list'),
    path('send/<str:username>/', views.send_request_view, name='send'),
    path('respond/<int:request_id>/', views.respond_request_view, name='respond'),
    path('unfriend/<str:username>/', views.unfriend_view, name='unfriend'),
    path('api/pending-count/', views.pending_count_api, name='pending_count'),
]
