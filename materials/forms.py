from django import forms
from .models import Material


class MaterialUploadForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ('title', 'description', 'subject', 'level', 'file_type', 'file',  'preview_image')
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g. Complete Physics Notes - Upper Sixth'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe what this material covers...'}),
        }
        help_texts = {
            'file': 'Accepted: PDF, Word, PowerPoint, Images, ZIP (max 50MB)',
        }
