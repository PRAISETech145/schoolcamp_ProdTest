from django.db import models
from django.conf import settings
from taggit.managers import TaggableManager
from PIL import Image
import os
import io
from django.core.files.base import ContentFile
import cloudinary.uploader  # Cloudinary upload


def question_image_upload_path(instance, filename):
    """Generate upload path for question images."""
    return f'question_images/{instance.author.id}/{filename}'


class Question(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    title = models.CharField(max_length=300)
    body = models.TextField()
    tags = TaggableManager(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to=question_image_upload_path, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        """Override save to resize image if needed."""
        # Check if this is a new image or image changed
        is_new_image = False
        if self.pk:
            try:
                old_instance = Question.objects.get(pk=self.pk)
                if self.image and self.image != old_instance.image:
                    is_new_image = True
            except Question.DoesNotExist:
                is_new_image = bool(self.image)
        else:
            is_new_image = bool(self.image)

        # Save the model first
        super().save(*args, **kwargs)

        # Process image if it's new (works with both local and Cloudinary storage)
        if is_new_image and self.image:
            try:
                # Check if using Cloudinary storage
                from django.core.files.storage import default_storage
                if default_storage.__class__.__name__ == 'MediaCloudinaryStorage':
                    # Cloudinary storage - transformations happen on upload via eager params
                    # No local processing needed
                    pass
                else:
                    # Local storage - process locally
                    img_path = self.image.path
                    if os.path.exists(img_path):
                        with Image.open(img_path) as img:
                            # Convert to RGB if necessary (e.g., PNG with transparency)
                            if img.mode in ('RGBA', 'LA', 'P'):
                                img = img.convert('RGB')

                            # Resize if larger than max dimensions
                            max_width = 1024
                            max_height = 1024
                            if img.width > max_width or img.height > max_height:
                                # Calculate new size maintaining aspect ratio
                                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

                                # Save with quality 85 to reduce file size significantly
                                img.save(img_path, quality=85, optimize=True)
            except Exception as e:
                # Log error but don't break save
                import sys
                print(f"ERROR processing image for Question {self.pk}: {e}", file=sys.stderr)
                pass

    def __str__(self):
        return self.title

    def like_count(self):
        return self.likes.count()

    def reply_count(self):
        return self.replies.count()

    def is_liked_by(self, user):
        if user.is_authenticated:
            return self.likes.filter(user=user).exists()
        return False


class Reply(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='replies'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='replies'
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_accepted = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Reply by {self.author.username} on '{self.question.title}'"

    def like_count(self):
        return self.likes.count()

    def is_liked_by(self, user):
        if not user or not user.is_authenticated:
            return False
        return self.likes.filter(user=user).exists()


class Like(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='liked_questions'
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='likes'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'question')

    def __str__(self):
        return f"{self.user.username} likes '{self.question.title}'"


class ReplyLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='liked_replies'
    )
    reply = models.ForeignKey(
        Reply,
        on_delete=models.CASCADE,
        related_name='likes'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'reply')

    def __str__(self):
        return f"{self.user.username} likes reply by '{self.reply.author.username}'"
