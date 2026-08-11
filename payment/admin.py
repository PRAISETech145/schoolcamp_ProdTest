from django.contrib import admin
from .models import Subscription, Payment


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'trial_start', 'trial_end', 'paid_until']
    list_filter = ['status']
    search_fields = ['user__username']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'provider', 'phone_number', 'amount', 'status', 'reference', 'created_at']
    list_filter = ['status', 'provider']
    search_fields = ['user__username', 'reference', 'phone_number']
    readonly_fields = ['created_at', 'confirmed_at']