from django.contrib import admin
from .models import Timetable, Course, TimetableShareRequest


@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'semester', 'academic_year', 'is_active', 'is_shared', 'created_at']
    list_filter = ['semester', 'is_active', 'is_shared']
    search_fields = ['name', 'user__username']
    readonly_fields = ['share_token']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'timetable', 'day_of_week', 'start_time', 'end_time', 'lecturer', 'room']
    list_filter = ['day_of_week', 'timetable__semester']
    search_fields = ['name', 'code', 'lecturer']


@admin.register(TimetableShareRequest)
class TimetableShareRequestAdmin(admin.ModelAdmin):
    list_display = ['from_user', 'to_user', 'timetable', 'seen', 'created_at']
    list_filter = ['seen']
