from django.db import models
from django.conf import settings


SUBJECT_CHOICES = [
    ('mathematics', 'Mathematics'), ('physics', 'Physics'),
    ('chemistry', 'Chemistry'), ('biology', 'Biology'),
    ('english', 'English'), ('french', 'French'),
    ('history', 'History'), ('geography', 'Geography'),
    ('economics', 'Economics'), ('computer_science', 'Computer Science'),
    ('other', 'Other'),
]

LEVEL_CHOICES = [
    ('form1', 'Form 1'), ('form2', 'Form 2'), ('form3', 'Form 3'),
    ('form4', 'Form 4'), ('form5', 'Form 5'),
    ('lower6', 'Lower Sixth'), ('upper6', 'Upper Sixth'),
    ('university', 'University'), ('all', 'All Levels'),
]

DIFFICULTY_CHOICES = [
    ('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard'),
]

QUESTION_TYPE_CHOICES = [
    ('mcq', 'Multiple Choice'),
    ('truefalse', 'True / False'),
]


class Quiz(models.Model):
    title = models.CharField(max_length=300)
    description = models.TextField(max_length=800, blank=True)
    subject = models.CharField(max_length=30, choices=SUBJECT_CHOICES)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='all')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    duration_minutes = models.PositiveIntegerField(default=30, help_text='Time limit in minutes')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quizzes'
    )
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Quizzes'

    def __str__(self):
        return self.title

    def question_count(self):
        return self.questions.count()

    def attempt_count(self):
        return self.attempts.count()

    def difficulty_color(self):
        return {'easy': 'success', 'medium': 'warning', 'hard': 'danger'}.get(self.difficulty, 'secondary')


class QuizQuestion(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPE_CHOICES, default='mcq')
    text = models.TextField()
    explanation = models.TextField(blank=True, help_text='Explanation shown after answering')
    points = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"Q{self.order}: {self.text[:60]}"


class QuizAnswer(models.Model):
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name='answers')
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        mark = '✓' if self.is_correct else '✗'
        return f"{mark} {self.text[:50]}"


class QuizAttempt(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_attempts'
    )
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    score = models.PositiveIntegerField(default=0)
    max_score = models.PositiveIntegerField(default=0)
    percentage = models.FloatField(default=0.0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_complete = models.BooleanField(default=False)
    time_taken_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.user.username} → {self.quiz.title} [{self.score}/{self.max_score}]"

    def grade_label(self):
        p = self.percentage
        if p >= 80: return ('A', 'success')
        elif p >= 70: return ('B', 'primary')
        elif p >= 60: return ('C', 'info')
        elif p >= 50: return ('D', 'warning')
        else: return ('F', 'danger')


class QuizAttemptAnswer(models.Model):
    """Stores each answer the user gave in a quiz attempt."""
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE)
    selected_answer = models.ForeignKey(
        QuizAnswer, on_delete=models.SET_NULL, null=True, blank=True
    )
    is_correct = models.BooleanField(default=False)

    class Meta:
        unique_together = ('attempt', 'question')
