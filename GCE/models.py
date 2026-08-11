import uuid
import os
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

SUBJECT_CHOICES = [
    ('mathematics', 'Mathematics'),
    ('physics', 'Physics'),
    ('chemistry', 'Chemistry'),
    ('biology', 'Biology'),
    ('english', 'English Language'),
    ('french', 'French Language'),
    ('history', 'History'),
    ('geography', 'Geography'),
    ('economics', 'Economics'),
    ('computer_science', 'Computer Science'),
    ('philosophy', 'Philosophy'),
    ('literature', 'Literature'),
    ('other', 'Other'),
]

FILE_TYPE_CHOICES = [
    ('pdf', 'PDF Document'), ('doc', 'Word Document'),
    ('ppt', 'PowerPoint'), ('image', 'Image'),
    ('zip', 'ZIP Archive'), ('other', 'Other'),
]

SOLUTION_PRICE = 50  # XAF — fixed price for every solution download

def material_upload_path(instance, filename):
    """Upload path for Material files."""
    ext = filename.split('.')[-1]
    subject_slug = instance.subject.slug if instance.subject else 'general'
    return f'GCE/pdfs/{subject_slug}/{uuid.uuid4().hex}.{ext}'


def solution_upload_path(instance, filename):
    """Upload path for Solutions files."""
    ext = filename.split('.')[-1]
    subject_slug = instance.subject_Name.slug if instance.subject_Name else 'general'
    return f'GCE/solutions/{subject_slug}/{uuid.uuid4().hex}.{ext}'


class Subject(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=10, default='📄')
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Material(models.Model):
    LEVEL_CHOICES = [
        ('AL',   'Advanced LEVEL'),
        ('OL', 'Ordinary LEVEL'),
        ('university','University'),
        ('all',       'All Levels'),
    ]

    title       = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    subject     = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, related_name='materials')
    level       = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='All Levels')
    file        = models.FileField(upload_to=material_upload_path)
    price       = models.DecimalField(max_digits=10, decimal_places=0, default=25)
    is_free     = models.BooleanField(default=False)
    pages       = models.PositiveIntegerField(default=0, help_text='Number of pages')
    downloads   = models.PositiveIntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)
    is_active   = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def file_size_mb(self):
        try:
            size = self.file.size
            return round(size / (1024 * 1024), 1)
        except Exception:
            return 0

    def user_has_access(self, user):
        """Check if a user can download this material."""
        if self.is_free:
            return True
        if not user.is_authenticated:
            return False
        return MaterialPurchase.objects.filter(
            user=user,
            material=self,
            is_valid=True,
        ).exists()


class MaterialPurchase(models.Model):
    """Records a student's purchase of a material."""
    user         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='material_purchases')
    material     = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='purchases')
    amount_paid  = models.DecimalField(max_digits=10, decimal_places=0)
    provider     = models.CharField(max_length=20)        # mtn / orange
    phone_number = models.CharField(max_length=20)
    reference    = models.CharField(max_length=100, unique=True)
    status       = models.CharField(max_length=20, default='pending')  # pending/completed/failed
    is_valid     = models.BooleanField(default=False)
    purchased_at = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'material')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} → {self.material.title} ({self.status})"

    def confirm(self):
        self.status = 'completed'
        self.is_valid = True
        self.purchased_at = timezone.now()
        self.save()
        Material.objects.filter(pk=self.material.pk).update(
            downloads=models.F('downloads') + 1
        )


class Solutions(models.Model):
    subject_Name    = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True)
    paper           = models.ForeignKey(Material, on_delete=models.PROTECT, null=True)
    solution        = models.FileField(upload_to=solution_upload_path)
    is_approved     = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
    title           = models.CharField(max_length=300)
    description     = models.TextField(max_length=1000)
    download_count  = models.PositiveIntegerField(default=0)
    file_type       = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES, default='pdf')
    # Solutions always cost SOLUTION_PRICE (50 XAF). No free solutions.

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.description})"

    @property
    def price(self):
        """Fixed price for every solution."""
        return SOLUTION_PRICE

    def file_size_display(self):
        try:
            size = self.solution.size
            if size < 1024:
                return f'{size} B'
            elif size < 1024 * 1024:
                return f'{size/1024:.1f} KB'
            else:
                return f'{size/(1024*1024):.1f} MB'
        except Exception:
            return 'Unknown'

    def file_icon(self):
        return {'pdf': '📄', 'doc': '📝', 'ppt': '📊', 'image': '🖼️', 'zip': '🗜️'}.get(self.file_type, '📁')

    def user_has_access(self, user):
        """Check if a user has paid for this solution."""
        if not user.is_authenticated:
            return False
        return SolutionPurchase.objects.filter(
            user=user,
            solution=self,
            is_valid=True,
        ).exists()


class SolutionPurchase(models.Model):
    """Records a student's purchase of a solution (50 XAF)."""
    user         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='solution_purchases')
    solution     = models.ForeignKey(Solutions, on_delete=models.CASCADE, related_name='purchases')
    amount_paid  = models.DecimalField(max_digits=10, decimal_places=0, default=SOLUTION_PRICE)
    provider     = models.CharField(max_length=20)        # mtn / orange
    phone_number = models.CharField(max_length=20)
    reference    = models.CharField(max_length=100, unique=True)
    status       = models.CharField(max_length=20, default='pending')  # pending/completed/failed
    is_valid     = models.BooleanField(default=False)
    purchased_at = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'solution')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} → {self.solution.title} ({self.status})"

    def confirm(self):
        self.status = 'completed'
        self.is_valid = True
        self.purchased_at = timezone.now()
        self.save()
        Solutions.objects.filter(pk=self.solution.pk).update(
            download_count=models.F('download_count') + 1
        )


class DownloadToken(models.Model):
    """
    One-time secure download token.
    Generated after purchase confirmed — expires after 1 use or 7 days.
    """
    token       = models.UUIDField(default=uuid.uuid4, unique=True)
    purchase    = models.ForeignKey(MaterialPurchase, on_delete=models.CASCADE, related_name='tokens', null=True, blank=True)
    solution_purchase = models.ForeignKey(SolutionPurchase, on_delete=models.CASCADE, related_name='tokens', null=True, blank=True)
    used        = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    expires_at  = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        return not self.used and timezone.now() < self.expires_at

    def __str__(self):
        if self.purchase:
            label = self.purchase.material.title
        elif self.solution_purchase:
            label = self.solution_purchase.solution.title
        else:
            label = 'Unknown'
        return f"Token for {label} ({'used' if self.used else 'valid'})"