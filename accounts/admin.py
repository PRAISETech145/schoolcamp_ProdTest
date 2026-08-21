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
