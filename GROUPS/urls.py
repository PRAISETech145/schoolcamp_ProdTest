from django.urls import path
from . import views

app_name = 'GROUPS'

urlpatterns = [
    path('', views.groups_list_view, name='list'),
    path('create/', views.create_group_view, name='create'),
    path('<int:pk>/', views.group_detail_view, name='detail'),
    path('<int:pk>/edit/', views.edit_group_view, name='edit'),
    path('<int:pk>/delete/', views.delete_group_view, name='delete'),
    path('<int:pk>/join/', views.join_group_view, name='join'),
    path('<int:pk>/leave/', views.leave_group_view, name='leave'),
    path('<int:pk>/invite/<str:username>/', views.invite_member_view, name='invite'),
    path('<int:pk>/respond/', views.respond_invite_view, name='respond_invite'),
    path('<int:pk>/requests/<int:member_id>/approve/', views.approve_request_view, name='approve_request'),
    path('<int:pk>/members/<int:member_id>/set-admin/', views.set_admin_view, name='set_admin'),
    path('<int:pk>/members/<int:member_id>/remove/', views.remove_member_view, name='remove_member'),
    path('<int:pk>/posts/<int:post_id>/delete/', views.delete_post_view, name='delete_post'),
]
