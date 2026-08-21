from django.urls import path
from . import views

app_name = 'forum'

urlpatterns = [
    path('health/', views.health_check, name='health'),
    path('', views.home_view, name='home'),
    path('ask/', views.post_question_view, name='ask'),
    path('question/<int:pk>/', views.question_detail_view, name='detail'),
    path('question/<int:pk>/edit/', views.edit_question_view, name='edit_question'),
    path('question/<int:pk>/delete/', views.delete_question_view, name='delete_question'),
    path('question/<int:pk>/like/', views.toggle_like_view, name='like'),
    path('reply/<int:pk>/like/', views.toggle_reply_like_view, name='reply_like'),
    path('reply/<int:pk>/delete/', views.delete_reply_view, name='delete_reply'),
    path('reply/<int:pk>/accept/', views.accept_reply_view, name='accept_reply'),
]
