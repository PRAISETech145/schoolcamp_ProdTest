from django.contrib import admin
from .models import Quiz, QuizQuestion, QuizAnswer, QuizAttempt


class QuizAnswerInline(admin.TabularInline):
    model = QuizAnswer
    extra = 4


class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 1
    show_change_link = True


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'level', 'difficulty', 'question_count', 'attempt_count', 'is_published', 'created_at')
    list_filter = ('subject', 'level', 'difficulty', 'is_published')
    search_fields = ('title',)
    inlines = [QuizQuestionInline]


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'quiz', 'question_type', 'points', 'order')
    inlines = [QuizAnswerInline]


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz', 'score', 'max_score', 'percentage', 'is_complete', 'started_at')
    list_filter = ('is_complete',)
