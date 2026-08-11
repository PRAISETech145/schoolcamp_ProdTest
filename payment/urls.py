from django.urls import path
from . import views

app_name = 'payment'

urlpatterns = [
    path('', views.payment_wall, name='wall'),
    path('initiate/', views.initiate_payment, name='initiate'),
    path('pending/<int:pk>/', views.payment_pending, name='pending'),
    path('status/<int:pk>/', views.payment_status, name='status'),
    path('confirm/<int:pk>/', views.confirm_payment, name='confirm'),  # demo only
    path('success/', views.payment_success, name='success'),
    path('failed/<int:pk>/', views.payment_failed, name='failed'),
    path('subscription/', views.subscription_status, name='subscription'),
    path('webhook/', views.payment_webhook, name='webhook'),
]