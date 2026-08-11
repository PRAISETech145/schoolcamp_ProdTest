from django import forms
from .models import Group, GroupPost


class GroupCreateForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ('name', 'description', 'visibility', 'cover_image')
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'e.g. Form 5 Science Study Group',
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'What is this group about?',
                'class': 'form-control'
            }),
            'visibility': forms.RadioSelect(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['visibility'].widget = forms.RadioSelect(
            attrs={'class': 'form-check-input'}
        )


class GroupEditForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ('name', 'description', 'visibility', 'cover_image')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'visibility': forms.RadioSelect(attrs={'class': 'form-check-input'}),
        }


class GroupPostForm(forms.ModelForm):
    class Meta:
        model = GroupPost
        fields = ('content',)
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Write something to the group...',
                'class': 'form-control'
            }),
        }
        labels = {'content': ''}


class InviteMemberForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter username to invite',
            'class': 'form-control',
            'autocomplete': 'off',
        }),
        label='Invite by username'
    )
