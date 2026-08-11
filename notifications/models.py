from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone


class Notification(models.Model):
    """
    Model for user notifications.
    """
    NOTIFICATION_TYPES = [
        ('message', 'New Message'),
        ('friend_request', 'Friend Request'),
        ('group_invite', 'Group Invitation'),
        ('group_message', 'New Group Message'),
        ('like', 'New Like'),
        ('reply', 'New Reply'),
        ('subscription_expiry', 'Subscription Expiry'),
        ('subscription_expiring_soon', 'Subscription Expiring Soon'),
        ('other', 'Other'),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications_from',
        null=True,
        blank=True
    )
    verb = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES,
        default='other'
    )
    # Generic foreign key to link to any model (e.g., Message, FriendRequest, etc.)
    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    target_object_id = models.PositiveIntegerField(null=True, blank=True)
    target = GenericForeignKey('target_content_type', 'target_object_id')

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f'{self.recipient.username} - {self.verb}'

    def mark_as_read(self):
        self.is_read = True
        self.save(update_fields=['is_read'])

    @property
    def is_recent(self):
        """Return True if notification was created in the last 24 hours."""
        return (timezone.now() - self.created_at).days < 1