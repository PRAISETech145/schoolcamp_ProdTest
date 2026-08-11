from django import forms
from .models import Timetable, Course, SUBJECT_COLORS


class TimetableForm(forms.ModelForm):
    class Meta:
        model = Timetable
        fields = ['name', 'semester', 'academic_year', 'is_shared']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Year 2 Semester 1',
            }),
            'semester': forms.Select(attrs={'class': 'form-select'}),
            'academic_year': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '2024/2025',
            }),
            'is_shared': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['name', 'code', 'lecturer', 'room', 'day_of_week',
                  'start_time', 'end_time', 'color', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Data Structures & Algorithms',
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. CSC301',
            }),
            'lecturer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Dr. Ndongo',
            }),
            'room': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Amphitheatre A',
            }),
            'day_of_week': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
            }),
            'end_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
            }),
            'color': forms.Select(attrs={'class': 'form-select color-select'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional notes about this course...',
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and end_time:
            if end_time <= start_time:
                raise forms.ValidationError("End time must be after start time.")

        return cleaned_data
