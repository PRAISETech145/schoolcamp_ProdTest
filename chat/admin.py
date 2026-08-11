from django.contrib import admin
from .models import DirectConversation, DirectMessage, GroupMessage

@admin.register(DirectConversation)
class DirectConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at', 'updated_at']

@admin.register(DirectMessage)
class DirectMessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'conversation', 'content', 'is_read', 'created_at']

@admin.register(GroupMessage)
class GroupMessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'group', 'content', 'created_at']
