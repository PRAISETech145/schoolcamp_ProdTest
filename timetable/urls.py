from django.urls import path
from . import views

app_name = 'timetable'

urlpatterns = [
    # Dashboard
    path('', views.timetable_dashboard, name='dashboard'),

    # Timetable CRUD
    path('create/', views.timetable_create, name='create'),
    path('<int:pk>/', views.timetable_detail, name='detail'),
    path('<int:pk>/edit/', views.timetable_edit, name='edit'),
    path('<int:pk>/delete/', views.timetable_delete, name='delete'),
    path('<int:pk>/set-active/', views.timetable_set_active, name='set_active'),

    # Course CRUD
    path('<int:timetable_pk>/add-course/', views.course_add, name='course_add'),
    path('course/<int:pk>/edit/', views.course_edit, name='course_edit'),
    path('course/<int:pk>/delete/', views.course_delete, name='course_delete'),

    # Views
    path('<int:pk>/day/<int:day>/', views.day_view, name='day_view'),
    path('<int:pk>/free-periods/', views.free_periods, name='free_periods'),

    # Sharing
    path('<int:pk>/share/', views.timetable_share, name='share'),
    path('shared-with-me/', views.shared_with_me, name='shared_with_me'),
    path('shared/<int:share_id>/', views.shared_timetable_view, name='shared_timetable_view'),
    path('shared/<str:token>/', views.timetable_public_view, name='public_view'),

    # Shared with me
    

    # API
    path('<int:pk>/api/courses/', views.api_courses_json, name='api_courses'),
]