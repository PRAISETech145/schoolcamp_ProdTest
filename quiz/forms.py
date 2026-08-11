from django import forms
from .models import Quiz, QuizQuestion, QuizAnswer


class QuizCreateForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ('title', 'description', 'subject', 'level', 'difficulty', 'duration_minutes')
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g. Form 5 Chemistry Mock Exam'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'What does this quiz cover?'}),
            'duration_minutes': forms.NumberInput(attrs={'min': 1, 'max': 180}),
        }


class QuizQuestionForm(forms.ModelForm):
    class Meta:
        model = QuizQuestion
        fields = ('question_type', 'text', 'explanation', 'points')
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter the question text...'}),
            'explanation': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional: explain the correct answer'}),
        }


class QuizAnswerForm(forms.ModelForm):
    class Meta:
        model = QuizAnswer
        fields = ('text', 'is_correct')
        widgets = {
            'text': forms.TextInput(attrs={'placeholder': 'Answer option text'}),
        }


QuizAnswerFormSet = forms.inlineformset_factory(
    QuizQuestion, QuizAnswer,
    form=QuizAnswerForm,
    extra=4,
    max_num=4,
    
)
