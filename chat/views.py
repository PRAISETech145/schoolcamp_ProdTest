from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import DirectConversation, DirectMessage, GroupMessage
from GROUPS.models import Group, GroupMember
from payment.views import subscription_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

import os

User = get_user_model()

# Allowed file types
ALLOWED_EXTENSIONS = {
    'image': ['jpg', 'jpeg', 'png', 'gif', 'webp'],
    'file':  ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'zip'],
    'voice': ['webm', 'ogg', 'mp3', 'wav', 'm4a'],
}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB


def get_message_type(filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    for msg_type, exts in ALLOWED_EXTENSIONS.items():
        if ext in exts:
            return msg_type
    return 'file'


@login_required
def inbox(request):
    conversations = DirectConversation.objects.filter(
        participants=request.user
    ).prefetch_related('participants', 'messages').order_by('-updated_at')

    conv_data = []
    for conv in conversations:
        other_user = conv.other_participant(request.user)
        if not other_user:
            continue
        last_msg = conv.messages.last()
        conv_data.append({
            'conv': conv,
            'other_user': other_user,
            'last_msg': last_msg,
            'unread': conv.unread_count(request.user),
        })

    my_groups = Group.objects.filter(
        memberships__user=request.user,
        memberships__status='active'
    ).order_by('name')

    return render(request, 'chat/inbox.html', {
        'conversations': conv_data,
        'my_groups': my_groups,
    })


@login_required
@subscription_required
def direct_chat(request, username):
    other_user = get_object_or_404(User, username=username)
    if other_user == request.user:
        return redirect('chat:inbox')

    conv = DirectConversation.objects.filter(
        participants=request.user
    ).filter(participants=other_user).first()

    if not conv:
        conv = DirectConversation.objects.create()
        conv.participants.add(request.user, other_user)

    chat_messages = conv.messages.select_related('sender').all()
    conv.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    return render(request, 'chat/direct_chat.html', {
        'conversation': conv,
        'other_user': other_user,
        'chat_messages': chat_messages,
    })


@login_required
@subscription_required
def group_chat(request, group_id):
    group = get_object_or_404(Group, pk=group_id)
    if not group.is_member(request.user):
        return redirect('groups:detail', pk=group_id)
    chat_messages = GroupMessage.objects.filter(
        group=group
    ).select_related('sender').order_by('created_at')
    # Mark messages as read when user opens group chat
    GroupMessage.objects.filter(group=group).exclude(sender=request.user).update(message_status='read')
    members = group.memberships.filter(
        status='active'
    ).select_related('user').order_by('role')
    return render(request, 'chat/group_chat.html', {
        'group': group,
        'chat_messages': chat_messages,
        'members': members,
    })


# ── File Upload Endpoint ──────────────────────────────────────

@login_required
@subscription_required
@require_POST
def upload_file(request):
    """
    Handles file/voice/image uploads for direct chat.
    Called via AJAX from the chat UI before sending via WebSocket.
    Returns the saved message ID and file URL.
    """
    conversation_id = request.POST.get('conversation_id')
    uploaded_file   = request.FILES.get('file')

    if not uploaded_file or not conversation_id:
        return JsonResponse({'error': 'Missing file or conversation'}, status=400)

    # Size check
    if uploaded_file.size > MAX_FILE_SIZE:
        return JsonResponse({'error': 'File too large. Max 25MB.'}, status=400)

    # Verify user is participant
    conv = get_object_or_404(
        DirectConversation, pk=conversation_id
    )
    if not conv.participants.filter(pk=request.user.pk).exists():
        return JsonResponse({'error': 'Not a participant'}, status=403)

    msg_type  = get_message_type(uploaded_file.name)
    file_name = uploaded_file.name

    message = DirectMessage.objects.create(
        conversation  = conv,
        sender        = request.user,
        message_type  = msg_type,
        content       = '',
        file          = uploaded_file,
        file_name     = file_name,
        file_size     = uploaded_file.size,
    )

    # Update conversation timestamp
    conv.updated_at = timezone.now()
    conv.save(update_fields=['updated_at'])

    return JsonResponse({
        'message_id':  message.id,
        'message_type': msg_type,
        'file_url':    message.file_url,
        'file_name':   file_name,
        'file_size':   message.file_size_display,
        'sender_username': request.user.username,
        'timestamp':   message.created_at.strftime('%H:%M'),
    })


@login_required
@subscription_required
@require_POST
def upload_group_file(request, group_id):
    """File upload for group chat."""
    group = get_object_or_404(Group, pk=group_id)
    if not group.is_member(request.user):
        return JsonResponse({'error': 'Not a member'}, status=403)

    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        return JsonResponse({'error': 'No file provided'}, status=400)

    if uploaded_file.size > MAX_FILE_SIZE:
        return JsonResponse({'error': 'File too large. Max 25MB.'}, status=400)

    msg_type = get_message_type(uploaded_file.name)
    message = GroupMessage.objects.create(
        group        = group,
        sender       = request.user,
        message_type = msg_type,
        file         = uploaded_file,
        file_name    = uploaded_file.name,
        file_size    = uploaded_file.size,
    )

    return JsonResponse({
        'message_id':      message.id,
        'message_type':    msg_type,
        'file_url':        message.file_url,
        'file_name':       uploaded_file.name,
        'file_size':       message.file_size_display,
        'sender_username': request.user.username,
        'timestamp':       message.created_at.strftime('%H:%M'),
    })


@login_required
@subscription_required
@require_POST
def upload_voice(request):
    conversation_id = request.POST.get('conversation_id')
    voice_file = request.FILES.get('voice')
    duration = int(request.POST.get('duration', 0))

    if not voice_file or not conversation_id:
        return JsonResponse({'error': 'Missing voice or conversation'}, status=400)

    conv = get_object_or_404(DirectConversation, pk=conversation_id)
    if not conv.participants.filter(pk=request.user.pk).exists():
        return JsonResponse({'error': 'Not a participant'}, status=403)

    message = DirectMessage.objects.create(
        conversation = conv,
        sender       = request.user,
        message_type = 'voice',
        file         = voice_file,
        file_name    = 'voice_message.webm',
        file_size    = voice_file.size,
        duration     = duration,
    )

    conv.updated_at = timezone.now()
    conv.save(update_fields=['updated_at'])

    return JsonResponse({
        'message_id':      message.id,
        'message_type':    'voice',
        'file_url':        message.file_url,
        'duration':        duration,
        'sender_username': request.user.username,
        'timestamp':       message.created_at.strftime('%H:%M'),
    })


@login_required
@subscription_required
@require_POST
def upload_group_voice(request, group_id):
    """Voice upload for group chat."""
    group = get_object_or_404(Group, pk=group_id)
    if not group.is_member(request.user):
        return JsonResponse({'error': 'Not a member'}, status=403)

    voice_file = request.FILES.get('voice')
    duration = int(request.POST.get('duration', 0))
    if not voice_file:
        return JsonResponse({'error': 'No voice provided'}, status=400)

    message = GroupMessage.objects.create(
        group        = group,
        sender       = request.user,
        message_type = 'voice',
        file         = voice_file,
        file_name    = 'voice_message.webm',
        file_size    = voice_file.size,
        duration     = duration,
    )

    return JsonResponse({
        'message_id':      message.id,
        'message_type':    'voice',
        'file_url':        message.file_url,
        'duration':        duration,
        'sender_username': request.user.username,
        'timestamp':       message.created_at.strftime('%H:%M'),
    })


@login_required
def new_message(request):
    query = request.GET.get('q', '').strip()
    results = []
    if query:
        results = User.objects.filter(
            username__icontains=query
        ).exclude(pk=request.user.pk)[:10]
    return render(request, 'chat/new_message.html', {
        'query': query,
        'results': results,
    })


@login_required
def unread_count(request):
    convs = DirectConversation.objects.filter(participants=request.user)
    total = sum(c.unread_count(request.user) for c in convs)
    return JsonResponse({'unread': total})
