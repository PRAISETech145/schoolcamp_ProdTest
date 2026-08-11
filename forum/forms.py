from django import forms
from .models import Question, Reply


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ('title', 'body', 'tags', 'image')
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'e.g. How do I solve quadratic equations?',
                'class': 'form-control'
            }),
            'body': forms.Textarea(attrs={
                'rows': 8,
                'placeholder': 'Describe your question in detail...',
                'class': 'form-control'
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
        }
        help_texts = {
            'tags': 'Add tags like: math, physics, chemistry, biology (comma-separated)',
            'image': 'Optional: Upload an image (max 5MB). Will be compressed to reduce file size while maintaining quality.',
        }


class ReplyForm(forms.ModelForm):
    class Meta:
        model = Reply
        fields = ('body',)
        widgets = {
            'body': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Write your answer or reply...',
                'class': 'form-control'
            }),
        }
        labels = {
            'body': 'Your Reply'
        }
