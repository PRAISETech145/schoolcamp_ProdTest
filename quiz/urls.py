from django.urls import path
from . import views

app_name = 'quiz'

urlpatterns = [
    path('', views.quiz_list_view, name='list'),
    path('create/', views.create_quiz_view, name='create'),
    path('<int:pk>/', views.quiz_detail_view, name='detail'),
    path('<int:pk>/start/', views.start_quiz_view, name='start'),
    path('<int:pk>/EditQuiz/', views.Edit_quiz_view, name='Edit_quiz'),
    path('quiz/<int:pk>/delete/', views.delete_quiz, name='delete_quiz'),
    path('<int:pk>/add-question/', views.add_question_view, name='add_question'),
    path('attempt/<int:attempt_pk>/q/<int:question_order>/', views.take_quiz_view, name='take'),
    path('attempt/<int:attempt_pk>/results/', views.quiz_results_view, name='results'),
]