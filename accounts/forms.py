from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'your@email.com'})
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Choose a username'})
    )
    school_name = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. GBHS Bamenda'})
    )
    region = forms.ChoiceField(
        choices=[('', '-- Select Region --')] + User._meta.get_field('region').choices,
        required=False
    )
    level = forms.ChoiceField(
        choices=[('', '-- Select Level --')] + User._meta.get_field('level').choices,
        required=False
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'school_name', 'region', 'level', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.school_name = self.cleaned_data.get('school_name', '')
        user.region = self.cleaned_data.get('region', '')
        user.level = self.cleaned_data.get('level', '')
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'placeholder': 'your@email.com', 'autofocus': True})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'})
    )


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'school_name', 'region', 'level', 'bio', 'avatar')
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Tell other students about yourself...'}),
            'school_name': forms.TextInput(attrs={'placeholder': 'e.g. GBHS Bamenda'}),
        }
