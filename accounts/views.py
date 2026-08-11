from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView
from django.urls import reverse_lazy
from .forms import RegisterForm, LoginForm, ProfileEditForm
from .models import User

# Import dashboard signals for activity tracking
try:
    from dashboard.signals import log_login_activity
except ImportError:
    log_login_activity = None


def register_view(request):
    if request.user.is_authenticated:
        return redirect('forum:home')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome to SchoolCamp, {user.username}! 🎉')
            return redirect('forum:home')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('forum:home')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Track login activity for streak
            if log_login_activity:
                log_login_activity(user)

            next_url = request.GET.get('next', 'forum:home')
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('accounts:login')


@login_required
def profile_view(request, username):
    profile_user = get_object_or_404(User, username=username)
   
    from forum.models import Question
    from friends.models import FriendRequest
    questions = Question.objects.filter(author=profile_user).order_by('-created_at')[:10]

    # Friend status
    friend_status = None
    if request.user != profile_user:
        sent = FriendRequest.objects.filter(sender=request.user, receiver=profile_user).first()
        received = FriendRequest.objects.filter(sender=profile_user, receiver=request.user).first()
        if sent:
            friend_status = sent.status  # pending / accepted / rejected
        elif received and received.status == 'accepted':
            friend_status = 'accepted'

    context = {
        'profile_user': profile_user,
        'questions': questions,
        'friend_status': friend_status,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def edit_profile_view(request):
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile', username=request.user.username)
    else:
        form = ProfileEditForm(instance=request.user)
    return render(request, 'accounts/edit_profile.html', {'form': form})
