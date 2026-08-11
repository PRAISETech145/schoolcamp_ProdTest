from django.contrib import admin
from .models import Group, GroupMember, GroupPost


class GroupMemberInline(admin.TabularInline):
    model = GroupMember
    extra = 0
    readonly_fields = ('joined_at',)
    fields = ('user', 'role', 'status', 'invited_by', 'joined_at')


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'visibility', 'member_count', 'created_at')
    list_filter = ('visibility', 'created_at')
    search_fields = ('name', 'description', 'creator__username')
    inlines = [GroupMemberInline]


@admin.register(GroupMember)
class GroupMemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'role', 'status', 'invited_by', 'joined_at')
    list_filter = ('role', 'status')
    search_fields = ('user__username', 'group__name')


@admin.register(GroupPost)
class GroupPostAdmin(admin.ModelAdmin):
    list_display = ('author', 'group', 'content', 'created_at')
    search_fields = ('author__username', 'group__name', 'content')
