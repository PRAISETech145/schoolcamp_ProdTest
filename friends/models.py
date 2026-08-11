from django.db import models
from django.conf import settings


class FriendRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_requests'
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_requests'
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('sender', 'receiver')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sender.username} → {self.receiver.username} [{self.status}]"

    @classmethod
    def are_friends(cls, user1, user2):
        return cls.objects.filter(
            models.Q(sender=user1, receiver=user2) |
            models.Q(sender=user2, receiver=user1),
            status='accepted'
        ).exists()

    @classmethod
    def get_friends(cls, user):
        """Return all friends of a user."""
        from accounts.models import User
        accepted = cls.objects.filter(
            models.Q(sender=user) | models.Q(receiver=user),
            status='accepted'
        ).select_related('sender', 'receiver')

        friends = []
        for req in accepted:
            friend = req.receiver if req.sender == user else req.sender
            friends.append(friend)
        return friends

    @classmethod
    def pending_count(cls, user):
        """Count of pending requests received by user."""
        return cls.objects.filter(receiver=user, status='pending').count()
