import uuid
from django.db import models
from django.conf import settings
from GROUPS.models import Group


class VideoCall(models.Model):
    CALL_TYPES = [
        ('direct', 'Direct Call'),
        ('group', 'Group Call'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('ringing', 'Ringing'),
        ('active', 'Active'),
        ('ended', 'Ended'),
        ('missed', 'Missed'),
        ('declined', 'Declined'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call_type = models.CharField(max_length=10, choices=CALL_TYPES, default='direct')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    # For direct calls
    caller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='calls_made'
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='calls_received', null=True, blank=True
    )
    conversation = models.ForeignKey(
        'DirectConversation', on_delete=models.CASCADE, related_name='video_calls', null=True, blank=True
    )

    # For group calls
    group = models.ForeignKey(
        Group, on_delete=models.CASCADE, related_name='video_calls', null=True, blank=True
    )

    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    connected_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration = models.PositiveIntegerField(default=0)  # seconds

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        if self.call_type == 'direct':
            return f"Call: {self.caller} -> {self.receiver} ({self.status})"
        return f"Group Call: {self.group} by {self.caller} ({self.status})"

    @property
    def duration_display(self):
        if self.duration < 60:
            return f"{self.duration}s"
        mins, secs = divmod(self.duration, 60)
        return f"{mins}m {secs}s"


class DirectConversation(models.Model):
    
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='direct_conversations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        users = self.participants.all()
        return f"DM: {' & '.join(u.username for u in users)}"

    def other_participant(self, user):
        return self.participants.exclude(pk=user.pk).first()

    def unread_count(self, user):
        return self.messages.filter(is_read=False).exclude(sender=user).count()
    
    

class DirectMessage(models.Model):
    MESSAGE_TYPES = [
        ('text',  'Text'),
        ('file',  'File'),
        ('voice', 'Voice'),
        ('image', 'Image'),
    ]

    MESSAGE_STATUS = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
    ]

    conversation = models.ForeignKey(
        DirectConversation, on_delete=models.CASCADE, related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_direct_messages'
    )
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    message_status = models.CharField(max_length=10, choices=MESSAGE_STATUS, default='sent')
    created_at = models.DateTimeField(auto_now_add=True)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    content = models.TextField(blank=True)
    file= models.FileField(upload_to='chat/files/', blank=True, null=True)
    file_name= models.CharField(max_length=255, blank=True)  # original filename
    file_size= models.PositiveIntegerField(default=0)        # bytes
    duration= models.PositiveIntegerField(default=0)
    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username}: {self.message_type} — {self.content[:40]}"

    @property
    def file_url(self):
        if self.file:
            return self.file.url
        return None

    @property
    def file_size_display(self):
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size // 1024} KB"
        else:
            return f"{self.file_size / (1024*1024):.1f} MB"
 



class GroupMessage(models.Model):
    MESSAGE_TYPES = [
        ('text',  'Text'),
        ('file',  'File'),
        ('voice', 'Voice'),
        ('image', 'Image'),
    ]

    MESSAGE_STATUS = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
    ]

    group = models.ForeignKey(
        'GROUPS.Group', on_delete=models.CASCADE, related_name='chat_messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='group_chat_messages'
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    message_status = models.CharField(max_length=10, choices=MESSAGE_STATUS, default='sent')
    content    = models.TextField(blank=True)
    file       = models.FileField(upload_to='chat/group_files/', blank=True, null=True)
    file_name  = models.CharField(max_length=255, blank=True)
    file_size  = models.PositiveIntegerField(default=0)
    duration   = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['created_at']


    def __str__(self):
        return f"{self.sender.username}: {self.content[:40]}"
    @property
    def file_url(self):
        if self.file:
            return self.file.url
        return None
