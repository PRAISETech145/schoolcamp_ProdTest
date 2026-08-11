from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard
    path('', views.dashboard_home, name='home'),

    # Activity feed
    path('activity/', views.activity_feed, name='activity_feed'),

    # Streak calendar
    path('streak/', views.streak_calendar, name='streak_calendar'),

    # Detailed stats
    path('stats/', views.stats_detail, name='stats_detail'),

    # Leaderboards
    path('leaderboard/', views.leaderboard, name='leaderboard'),

    # User profile dashboard
    path('user/<str:username>/', views.user_profile_dashboard, name='user_profile'),

    # API endpoints
    path('api/streak/', views.api_streak_status, name='api_streak'),
    path('api/weekly/', views.api_weekly_progress, name='api_weekly'),
    path('api/recent/', views.api_recent_activities, name='api_recent'),
]