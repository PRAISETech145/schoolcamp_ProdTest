from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import FriendRequest
from accounts.models import User
from payment.views import subscription_required

@login_required
def friends_list_view(request):
    """Show all friends and pending requests."""
    friends = FriendRequest.get_friends(request.user)
    pending_received = FriendRequest.objects.filter(
        receiver=request.user, status='pending'
    ).select_related('sender')
    pending_sent = FriendRequest.objects.filter(
        sender=request.user, status='pending'
    ).select_related('receiver')

    context = {
        'friends': friends,
        'pending_received': pending_received,
        'pending_sent': pending_sent,
    }
    return render(request, 'friends/friends_list.html', context)


@login_required
@require_POST
@subscription_required
def send_request_view(request, username):
    """Send a friend request to a user."""
    receiver = get_object_or_404(User, username=username)

    if receiver == request.user:
        messages.error(request, "You can't send a friend request to yourself.")
        return redirect('accounts:profile', username=username)

    # Check if already friends or request exists
    existing = FriendRequest.objects.filter(
        sender=request.user, receiver=receiver
    ).first()
    reverse_existing = FriendRequest.objects.filter(
        sender=receiver, receiver=request.user
    ).first()

    if existing:
        messages.info(request, f'Friend request already sent to {receiver.username}.')
    elif reverse_existing and reverse_existing.status == 'accepted':
        messages.info(request, f'You are already friends with {receiver.username}.')
    elif reverse_existing and reverse_existing.status == 'pending':
        # They already sent us a request – auto-accept
        reverse_existing.status = 'accepted'
        reverse_existing.responded_at = timezone.now()
        reverse_existing.save()
        messages.success(request, f'You are now friends with {receiver.username}! 🎉')
    else:
        FriendRequest.objects.create(sender=request.user, receiver=receiver)
        messages.success(request, f'Friend request sent to {receiver.username}!')

    return redirect('accounts:profile', username=username)


@login_required
@require_POST
@subscription_required
def respond_request_view(request, request_id):
    """Accept or reject a friend request."""
    friend_request = get_object_or_404(
        FriendRequest, pk=request_id, receiver=request.user, status='pending'
    )
    action = request.POST.get('action')  # 'accept' or 'reject'

    if action == 'accept':
        friend_request.status = 'accepted'
        friend_request.responded_at = timezone.now()
        friend_request.save()
        friend_request.sender.add_xp(5)
        messages.success(request, f'You are now friends with {friend_request.sender.username}! 🎉')
    elif action == 'reject':
        friend_request.status = 'rejected'
        friend_request.responded_at = timezone.now()
        friend_request.save()
        messages.info(request, f'Friend request from {friend_request.sender.username} declined.')

    return redirect('friends:list')


@login_required
@require_POST
def unfriend_view(request, username):
    """Remove a friend."""
    other_user = get_object_or_404(User, username=username)
    FriendRequest.objects.filter(
        sender=request.user, receiver=other_user, status='accepted'
    ).delete()
    FriendRequest.objects.filter(
        sender=other_user, receiver=request.user, status='accepted'
    ).delete()
    messages.info(request, f'You unfriended {other_user.username}.')
    return redirect('accounts:profile', username=username)


@login_required
def pending_count_api(request):
    """API: Return count of pending friend requests (for navbar badge)."""
    count = FriendRequest.pending_count(request.user)
    return JsonResponse({'count': count})
