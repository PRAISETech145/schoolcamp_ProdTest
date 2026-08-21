from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count
from django.views.decorators.http import require_POST
from functools import wraps
from .models import Question, Reply, Like, ReplyLike
from .forms import QuestionForm, ReplyForm
from payment.views import subscription_required


def health_check(request):
    """Lightweight health check for Railway - no DB access needed"""
    return HttpResponse("OK", status=200)


def ajax_like_required(view_func):
    
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {'error': 'Login required to like.', 'redirect': '/accounts/login/'},
                status=401
            )
        if request.method != 'POST':
            return JsonResponse({'error': 'POST request required.'}, status=405)
        return view_func(request, *args, **kwargs)
    return wrapper

def home_view(request):

    questions = Question.objects.annotate(
        like_cnt=Count('likes', distinct=True),
        reply_cnt=Count('replies', distinct=True)
    ).select_related('author').prefetch_related('tags')

    search = request.GET.get('q', '')
    tag = request.GET.get('tag', '')

    if search:
        questions = questions.filter(
            Q(title__icontains=search) | Q(body__icontains=search)
        )
    if tag:
        questions = questions.filter(tags__name__in=[tag])

    # Pass the set of question PKs liked by current user so template can show state
    liked_ids = set()
    if request.user.is_authenticated:
        liked_ids = set(
            Like.objects.filter(user=request.user)
            .values_list('question_id', flat=True)
        )

    context = {
        'questions': questions,
        'search': search,
        'active_tag': tag,
        'liked_ids': liked_ids,
    }
    return render(request, 'forum/home.html', context)


@login_required
@subscription_required
def post_question_view(request):
    """Post a new question."""
    if request.method == 'POST':
        form = QuestionForm(request.POST, request.FILES)
        if form.is_valid():
            question = form.save(commit=False)
            question.author = request.user
            question.save()
            form.save_m2m()  
            request.user.add_xp(3)
            messages.success(request, 'Question posted! 🎉')
            return redirect('forum:detail', pk=question.pk)
    else:
        form = QuestionForm()
    return render(request, 'forum/post_question.html', {'form': form})


def question_detail_view(request, pk):
    """Show question detail with replies."""
    question = get_object_or_404(
        Question.objects.select_related('author').prefetch_related('tags', 'replies__author'),
        pk=pk
    )
    question.views += 1
    question.save(update_fields=['views'])

    reply_form = ReplyForm()
    if request.method == 'POST' and request.user.is_authenticated:
        reply_form = ReplyForm(request.POST)
        if reply_form.is_valid():
            reply = reply_form.save(commit=False)
            reply.question = question
            reply.author = request.user
            reply.save()
            request.user.add_xp(5)
            messages.success(request, 'Reply posted!')
            return redirect('forum:detail', pk=pk)

    # Liked reply PKs for current user
    liked_reply_ids = set()
    if request.user.is_authenticated:
        liked_reply_ids = set(
            ReplyLike.objects.filter(user=request.user)
            .values_list('reply_id', flat=True)
        )

    context = {
        'question': question,
        'replies': question.replies.all(),
        'reply_form': reply_form,
        'user_liked': question.is_liked_by(request.user),
        'liked_reply_ids': liked_reply_ids,
    }
    return render(request, 'forum/detail.html', context)


@ajax_like_required
def toggle_like_view(request, pk):
    """
    AJAX endpoint — like/unlike a Question.

    POST /forum/question/<pk>/like/
    Returns: { liked: bool, count: int }
    """
    question = get_object_or_404(Question, pk=pk)
    like, created = Like.objects.get_or_create(user=request.user, question=question)

    if not created:
        like.delete()
        liked = False
    else:
        liked = True
        if request.user != question.author:
            question.author.add_xp(1)

    return JsonResponse({'liked': liked, 'count': question.like_count()})


@ajax_like_required
def toggle_reply_like_view(request, pk):

    reply = get_object_or_404(Reply, pk=pk)
    like, created = ReplyLike.objects.get_or_create(user=request.user, reply=reply)

    if not created:
        like.delete()
        liked = False
    else:
        liked = True
        if request.user != reply.author:
            reply.author.add_xp(1)

    return JsonResponse({'liked': liked, 'count': reply.like_count()})


@login_required
def edit_question_view(request, pk):
    question = get_object_or_404(Question, id=pk, author=request.user)
    if request.method == 'POST':
        form = QuestionForm(request.POST, request.FILES, instance=question)
        if form.is_valid():
            form.save()
            messages.success(request, 'Question updated!')
            return redirect('forum:detail', pk=pk)
    else:
        form = QuestionForm(instance=question)
    return render(request, 'forum/post_question.html', {'form': form, 'editing': True})


@login_required
def delete_question_view(request, pk):
    question = get_object_or_404(Question, id=pk, author=request.user)
    if request.method == 'POST':
        question.delete()
        messages.success(request, 'Question deleted.')
        return redirect('forum:home')
    return render(request, 'forum/confirm_delete.html', {'object': question})


@login_required
def delete_reply_view(request, pk):
    reply = get_object_or_404(Reply, id=pk, author=request.user)
    question_pk = reply.question.pk
    if request.method == 'POST':
        reply.delete()
        messages.success(request, 'Reply deleted.')
    return redirect('forum:detail', pk=question_pk)


@login_required
@require_POST
def accept_reply_view(request, pk):
    reply = get_object_or_404(Reply, id=pk)
    question = reply.question
    if request.user == question.author:
        question.replies.filter(is_accepted=True).update(is_accepted=False)
        reply.is_accepted = True
        reply.save()
        reply.author.add_xp(2)
        messages.success(request, 'Answer accepted! ✅')
    return redirect('forum:detail', pk=question.id)
