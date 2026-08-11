from django.db import models
from django.db import models
from django.conf import settings

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

LEVEL_CHOICES = [
    ('form1', 'Form 1'), ('form2', 'Form 2'), ('form3', 'Form 3'),
    ('form4', 'Form 4'), ('form5', 'Form 5'),
    ('lower6', 'Lower Sixth'), ('upper6', 'Upper Sixth'),
    ('university', 'University'), ('all', 'All Levels'),
]

FILE_TYPE_CHOICES = [
    ('pdf', 'PDF Document'), ('doc', 'Word Document'),
    ('ppt', 'PowerPoint'), ('image', 'Image'),
    ('zip', 'ZIP Archive'), ('other', 'Other'),
]


def material_upload_path(instance, filename):
    return f'materials/{instance.subject}/{filename}'


class Material(models.Model):
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='uploaded_materials'
    )
    title = models.CharField(max_length=300)
    description = models.TextField(max_length=1000)
    subject = models.CharField(max_length=30, choices=SUBJECT_CHOICES)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='all')
    file = models.FileField(upload_to=material_upload_path)
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES, default='pdf')
    preview_image = models.ImageField(upload_to='material_previews/', blank=True, null=True)
    download_count = models.PositiveIntegerField(default=0)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_subject_display()})"


    def price_display(self):
        return 'Free' if self.is_free() else f'{self.price:,} XAF'

    def file_size_display(self):
        try:
            size = self.file.size
            if size < 1024: return f'{size} B'
            elif size < 1024 * 1024: return f'{size/1024:.1f} KB'
            else: return f'{size/(1024*1024):.1f} MB'
        except Exception:
            return 'Unknown'

    def file_icon(self):
        return {'pdf':'📄','doc':'📝','ppt':'📊','image':'🖼️','zip':'🗜️'}.get(self.file_type,'📁')

class MaterialPurchase(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='purchases'
    )
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='purchases')
     
    purchased_at = models.DateTimeField(auto_now_add=True)
    amount_paid = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'material')

    def __str__(self):
        return f"{self.user.username} → {self.material.title}"
