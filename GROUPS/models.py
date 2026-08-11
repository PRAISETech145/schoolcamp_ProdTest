from django.db import models
from django.conf import settings


def group_cover_path(instance, filename):
    return f'groups/covers/{instance.pk}_{filename}'


class Group(models.Model):
    VISIBILITY_CHOICES = [
        ('public', 'Public Anyone can join, all members can invite'),
        ('private', 'Private Join by invite or request only'),
    ]

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_groups'
    )
    name = models.CharField(max_length=150)
    description = models.TextField(max_length=800, blank=True)
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='public')
    cover_image = models.ImageField(upload_to='groups/covers/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({'Public' if self.is_public else 'Private'})"

    @property
    def is_public(self):
        return self.visibility == 'public'

    @property
    def is_private(self):
        return self.visibility == 'private'

    def member_count(self):
        return self.memberships.filter(status='active').count()

    def get_membership(self, user):
        """Return GroupMember for a user or None."""
        return self.memberships.filter(user=user).first()

    def is_member(self, user):
        return self.memberships.filter(user=user, status='active').exists()

    def is_admin(self, user):
        return self.memberships.filter(
            user=user, status='active', role__in=['admin', 'creator']
        ).exists()

    def is_creator(self, user):
        return self.creator == user

    def can_invite(self, user):
        """
        Public: any active member can invite.
        Private: only admins/creator can invite.
        """
        if self.is_public:
            return self.is_member(user)
        return self.is_admin(user)


class GroupMember(models.Model):
    ROLE_CHOICES = [
        ('creator', 'Creator'),
        ('admin', 'Admin'),
        ('member', 'Member'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('pending', 'Pending Approval'),    
        ('invited', 'Invited'),              
        ('banned', 'Banned'),
    ]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='group_memberships'
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sent_invites'
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'user')
        ordering = ['role', 'joined_at']

    def __str__(self):
        return f"{self.user.username} in {self.group.name} [{self.role}/{self.status}]"

    @property
    def is_active(self):
        return self.status == 'active'


class GroupPost(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='posts')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='group_posts'
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.author.username} in {self.group.name}: {self.content[:50]}"
