from django.contrib.auth.models import AbstractUser
from django.db import models


CAMEROON_REGIONS = [
    ('adamawa', 'Adamawa'),
    ('centre', 'Centre'),
    ('east', 'East'),
    ('far_north', 'Far North'),
    ('littoral', 'Littoral'),
    ('north', 'North'),
    ('north_west', 'North West'),
    ('south', 'South'),
    ('south_west', 'South West'),
    ('west', 'West'),
]

SCHOOL_LEVELS = [
    ('form1', 'Form 1'),
    ('form2', 'Form 2'),
    ('form3', 'Form 3'),
    ('form4', 'Form 4'),
    ('form5', 'Form 5'),
    ('lower6', 'Lower Sixth'),
    ('upper6', 'Upper Sixth'),
    ('university', 'University'),
    ('other', 'Other'),
]


class User(AbstractUser):
    """
    Custom User model for SchoolCamp.
    Extends AbstractUser with Cameroon-specific fields.
    """
    email = models.EmailField(unique=True)
    school_name = models.CharField(max_length=200, blank=True)
    region = models.CharField(max_length=20, choices=CAMEROON_REGIONS, blank=True)
    level = models.CharField(max_length=20, choices=SCHOOL_LEVELS, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    xp_points = models.PositiveIntegerField(default=0)
    is_email_verified = models.BooleanField(default=False)
    date_joined_schoolcamp = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.username} ({self.email})"

    def get_avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return '/static/img/default_avatar.png'

    def add_xp(self, points):
        self.xp_points += points
        self.save(update_fields=['xp_points'])
