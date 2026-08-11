from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'school_name', 'region', 'level', 'xp_points', 'is_active', 'date_joined')
    list_filter = ('region', 'level', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'school_name')
    ordering = ('-date_joined',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('SchoolCamp Info', {
            'fields': ('school_name', 'region', 'level', 'bio', 'avatar', 'xp_points', 'is_email_verified')
        }),
    )
from payment.models import Payment
from django.contrib.auth import get_user_model
import uuid
User = get_user_model()  
u = User.objects.first()
ref = 'SC-' + uuid.uuid4().hex[:10].upper()
p = Payment.objects.create(user=u, provider='mtn', phone_number='682834990', amount=200, reference=ref, status='pending')
print('Reference:', p.reference)