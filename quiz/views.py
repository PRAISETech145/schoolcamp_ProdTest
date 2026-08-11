from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Avg, Count
from .models import Quiz, QuizQuestion, QuizAnswer, QuizAttempt, QuizAttemptAnswer
from .forms import QuizCreateForm, QuizQuestionForm, QuizAnswerFormSet
from payment.views import subscription_required
@login_required
@subscription_required
def quiz_list_view(request):
    """Browse all published quizzes."""
    quizzes = Quiz.objects.filter(is_published=True).annotate(
        q_count=Count('questions'),
        a_count=Count('attempts')
    ).select_related('created_by')

    subject = request.GET.get('subject', '')
    level = request.GET.get('level', '')
    difficulty = request.GET.get('difficulty', '')
    search = request.GET.get('q', '')

    if subject: quizzes = quizzes.filter(subject=subject)
    if level: quizzes = quizzes.filter(level=level)
    if difficulty: quizzes = quizzes.filter(difficulty=difficulty)
    if search: quizzes = quizzes.filter(Q(title__icontains=search) | Q(description__icontains=search))

    from .models import SUBJECT_CHOICES, LEVEL_CHOICES, DIFFICULTY_CHOICES
    context = {
        'quizzes': quizzes,
        'subject_choices': SUBJECT_CHOICES,
        'level_choices': LEVEL_CHOICES,
        'difficulty_choices': DIFFICULTY_CHOICES,
        'active_subject': subject,
        'active_level': level,
        'active_difficulty': difficulty,
        'search': search,
    }
    return render(request, 'quiz/list.html', context)


def quiz_detail_view(request, pk):
   
    quiz = get_object_or_404(Quiz, pk=pk, is_published=True)
    leaderboard = QuizAttempt.objects.filter(
        quiz=quiz, is_complete=True
    ).select_related('user').order_by('-percentage', 'time_taken_seconds')[:10]

    user_best = None
    if request.user.is_authenticated:
        user_best = QuizAttempt.objects.filter(
            quiz=quiz, user=request.user, is_complete=True
        ).order_by('-percentage').first()

    context = {
        'quiz': quiz,
        'leaderboard': leaderboard,
        'user_best': user_best,
    }
    return render(request, 'quiz/detail.html', context)


@login_required
@subscription_required
def start_quiz_view(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, is_published=True)
    if quiz.question_count() == 0:
        messages.error(request, 'This quiz has no questions yet.')
        return redirect('quiz:detail', pk=pk)

    attempt = QuizAttempt.objects.create(
        user=request.user,
        quiz=quiz,
        max_score=sum(q.points for q in quiz.questions.all()),
    )
    return redirect('quiz:take', attempt_pk=attempt.pk, question_order=1)


@login_required
@subscription_required
def take_quiz_view(request, attempt_pk, question_order):
    
    attempt = get_object_or_404(QuizAttempt, pk=attempt_pk, user=request.user, is_complete=False)
    quiz = attempt.quiz
    questions = list(quiz.questions.all())
    total = len(questions)

    if question_order < 1 or question_order > total:
        return redirect('quiz:results', attempt_pk=attempt_pk)

    question = questions[question_order - 1]
    existing = QuizAttemptAnswer.objects.filter(attempt=attempt, question=question).first()
    if request.method == 'POST' and not existing:
        answer_id = request.POST.get('answer')
        selected = QuizAnswer.objects.filter(pk=answer_id, question=question).first()
        is_correct = selected.is_correct if selected else False

        QuizAttemptAnswer.objects.create(
            attempt=attempt,
            question=question,
            selected_answer=selected,
            is_correct=is_correct,
        )
        if is_correct:
            attempt.score += question.points
            attempt.save(update_fields=['score'])

        # Go to next question or finish
        if question_order < total:
            return redirect('quiz:take', attempt_pk=attempt_pk, question_order=question_order + 1)
        else:
            # Finish the quiz
            attempt.is_complete = True
            attempt.completed_at = timezone.now()
            delta = (attempt.completed_at - attempt.started_at).seconds
            attempt.time_taken_seconds = delta
            attempt.percentage = (attempt.score / attempt.max_score * 100) if attempt.max_score > 0 else 0
            attempt.save()
            xp = int(attempt.percentage / 2)
            request.user.add_xp(xp)
            return redirect('quiz:results', attempt_pk=attempt_pk)

    context = {
        'attempt': attempt,
        'quiz': quiz,
        'question': question,
        'question_order': question_order,
        'total': total,
        'progress_pct': int((question_order - 1) / total * 100),
        'answers': question.answers.all(),
        'existing': existing,
        'duration_seconds': quiz.duration_minutes * 60,
    }
    return render(request, 'quiz/take.html', context)


@login_required
def quiz_results_view(request, attempt_pk):
    """Show results with score, grade, correct answers."""
    attempt = get_object_or_404(QuizAttempt, pk=attempt_pk, user=request.user, is_complete=True)
    answered = attempt.answers.select_related('question', 'selected_answer').prefetch_related('question__answers')
    grade, color = attempt.grade_label()
    context = {
        'attempt': attempt,
        'answered': answered,
        'grade': grade,
        'grade_color': color,
    }
    return render(request, 'quiz/results.html', context)


@login_required
@subscription_required
def create_quiz_view(request):
    """Staff/teachers can create quizzes."""
    if request.method == 'POST':
        form = QuizCreateForm(request.POST)
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.created_by = request.user
            quiz.save()
            request.user.add_xp(3)
            messages.success(request, f'Quiz "{quiz.title}" created! Now add questions.')
            return redirect('quiz:add_question', pk=quiz.pk)
    else:
        form = QuizCreateForm()
    return render(request, 'quiz/create.html', {'form': form})


@login_required
@subscription_required
def add_question_view(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, created_by=request.user)
    if request.method == 'POST':
        qform = QuizQuestionForm(request.POST)
        aformset = QuizAnswerFormSet(request.POST)
        if qform.is_valid() and aformset.is_valid():
            question = qform.save(commit=False)
            question.quiz = quiz
            question.order = quiz.question_count() + 1
            question.save()
            answers = aformset.save(commit=False)
            for ans in answers:
                ans.question = question
                ans.save()
            messages.success(request, 'Question added!')
            action = request.POST.get('action', 'another')
            if action == 'finish':
                return redirect('quiz:detail', pk=quiz.pk)
            return redirect('quiz:add_question', pk=quiz.pk)
    else:
        qform = QuizQuestionForm()
        aformset = QuizAnswerFormSet()

    context = {
        'quiz': quiz,
        'qform': qform,
        'aformset': aformset,
        'existing_questions': quiz.questions.prefetch_related('answers').all(),
    }
    return render(request, 'quiz/add_question.html', context)

def Edit_quiz_view(request,pk):
    quiz = get_object_or_404(Quiz, id=pk, created_by=request.user)
    if request.method == 'POST':
        form = QuizCreateForm(request.POST, instance=quiz)
        if form.is_valid():
            form.save()
            messages.success(request, 'Question updated!')
            return redirect('forum:detail', pk=pk)
    else:
        form = QuizCreateForm(instance=quiz)
    return render(request, 'quiz/delete.html', {'form': form, 'editing': True})

def delete_quiz(request,pk):
    quiz=get_object_or_404(Quiz,id=pk,created_by=request.user)
    if request.method == 'POST':
        quiz.delete()
        messages.success(request,'Quiz deleted successfully!')
        return redirect('forum:home')
    return render(request,'quiz/confirm_delete.html',{quiz:'quiz'})