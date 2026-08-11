from django.urls import path
from . import views

app_name = 'legal'

urlpatterns = [
    path('terms/',   views.terms,   name='terms'),
    path('privacy/', views.privacy, name='privacy'),
    path('payment/', views.payment, name='payment'),
    path('cookies/', views.cookies, name='cookies'),
]