from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, Count
from accounts.models import User
from .models import Group, GroupMember, GroupPost
from .forms import GroupCreateForm, GroupEditForm, GroupPostForm, InviteMemberForm
from payment.views import subscription_required


@login_required
@subscription_required
def groups_list_view(request):
    """Discover public groups + user's own groups."""
    public_groups = Group.objects.filter(visibility='public').annotate(
        mc=Count('memberships', filter=Q(memberships__status='active'))
    ).order_by('-created_at')

    search = request.GET.get('q', '')
    if search:
        public_groups = public_groups.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )

    my_groups = []
    pending_invites = []
    if request.user.is_authenticated:
        my_memberships = GroupMember.objects.filter(
            user=request.user, status='active'
        ).select_related('group')
        my_groups = [m.group for m in my_memberships]

        pending_invites = GroupMember.objects.filter(
            user=request.user, status='invited'
        ).select_related('group', 'invited_by')

    context = {
        'public_groups': public_groups,
        'my_groups': my_groups,
        'pending_invites': pending_invites,
        'search': search,
    }
    return render(request, 'groups/list.html', context)



@login_required
@subscription_required
def create_group_view(request):
    if request.method == 'POST':
        form = GroupCreateForm(request.POST, request.FILES)
        if form.is_valid():
            group = form.save(commit=False)
            group.creator = request.user
            group.save()
            # Creator automatically becomes first member with 'creator' role
            GroupMember.objects.create(
                group=group,
                user=request.user,
                role='creator',
                status='active'
            )
            request.user.add_xp(10)
            messages.success(request, f'Group "{group.name}" created! 🎉')
            return redirect('groups:detail', pk=group.pk)
    else:
        form = GroupCreateForm()
    return render(request, 'groups/create.html', {'form': form})



def group_detail_view(request, pk):
    group = get_object_or_404(Group, pk=pk)

    membership = None
    if request.user.is_authenticated:
        membership = group.get_membership(request.user)

    # Private group: non-members can only see name/description
    can_see_content = (
        group.is_public or
        (membership and membership.status == 'active')
    )

    posts = []
    members = []
    admins = []
    post_form = None
    invite_form = None

    if can_see_content:
        posts = group.posts.select_related('author').all()[:50]
        members = group.memberships.filter(status='active').select_related('user').order_by('role', 'joined_at')
        admins = [m for m in members if m.role in ('creator', 'admin')]

        if request.user.is_authenticated and membership and membership.status == 'active':
            post_form = GroupPostForm()
            if group.can_invite(request.user):
                invite_form = InviteMemberForm()

    # Handle post submission
    if request.method == 'POST' and request.user.is_authenticated:
        action = request.POST.get('action')

        if action == 'post' and membership and membership.status == 'active':
            post_form = GroupPostForm(request.POST)
            if post_form.is_valid():
                p = post_form.save(commit=False)
                p.group = group
                p.author = request.user
                p.save()
                messages.success(request, 'Post added!')
                return redirect('groups:detail', pk=pk)

        elif action == 'invite' and group.can_invite(request.user):
            invite_form = InviteMemberForm(request.POST)
            if invite_form.is_valid():
                username = invite_form.cleaned_data['username']
                return redirect('groups:invite', pk=pk, username=username)

    # Pending join requests (for admins)
    join_requests = []
    if request.user.is_authenticated and group.is_admin(request.user):
        join_requests = group.memberships.filter(status='pending').select_related('user')

    context = {
        'group': group,
        'membership': membership,
        'can_see_content': can_see_content,
        'posts': posts,
        'members': members,
        'admins': admins,
        'post_form': post_form,
        'invite_form': invite_form,
        'join_requests': join_requests,
        'is_admin': request.user.is_authenticated and group.is_admin(request.user),
        'is_creator': request.user.is_authenticated and group.is_creator(request.user),
    }
    return render(request, 'groups/detail.html', context)




@login_required
@require_POST
@subscription_required
def join_group_view(request, pk):
    group = get_object_or_404(Group, pk=pk)
    existing = group.get_membership(request.user)

    if existing and existing.status == 'active':
        messages.info(request, 'You are already a member.')
        return redirect('groups:detail', pk=pk)

    if existing and existing.status == 'banned':
        messages.error(request, 'You have been banned from this group.')
        return redirect('groups:detail', pk=pk)

    if group.is_public:
        if existing:
            existing.status = 'active'
            existing.save()
        else:
            GroupMember.objects.create(group=group, user=request.user, role='member', status='active')
        messages.success(request, f'You joined {group.name}!')
    else:
        # Private: create a join request
        if existing and existing.status == 'pending':
            messages.info(request, 'Your join request is already pending.')
        else:
            GroupMember.objects.get_or_create(
                group=group, user=request.user,
                defaults={'role': 'member', 'status': 'pending'}
            )
            messages.success(request, f'Join request sent to {group.name}. An admin will review it.')
    return redirect('groups:detail', pk=pk)


@login_required
@require_POST
def leave_group_view(request, pk):
    group = get_object_or_404(Group, pk=pk)
    if group.is_creator(request.user):
        messages.error(request, 'As creator, you cannot leave your own group. Transfer ownership or delete it.')
        return redirect('groups:detail', pk=pk)
    GroupMember.objects.filter(group=group, user=request.user).delete()
    messages.info(request, f'You left {group.name}.')
    return redirect('groups:list')


# ── INVITE ────────────────────────────────────────────────────────────────────

@login_required
def invite_member_view(request, pk, username):
    group = get_object_or_404(Group, pk=pk)

    if not group.can_invite(request.user):
        messages.error(request, 'You do not have permission to invite members.')
        return redirect('groups:detail', pk=pk)

    invited_user = get_object_or_404(User, username=username)

    if invited_user == request.user:
        messages.error(request, "You can't invite yourself.")
        return redirect('groups:detail', pk=pk)

    existing = group.get_membership(invited_user)
    if existing:
        if existing.status == 'active':
            messages.info(request, f'{invited_user.username} is already a member.')
        elif existing.status == 'invited':
            messages.info(request, f'{invited_user.username} already has a pending invite.')
        elif existing.status == 'banned':
            messages.error(request, f'{invited_user.username} is banned from this group.')
        return redirect('groups:detail', pk=pk)

    GroupMember.objects.create(
        group=group,
        user=invited_user,
        role='member',
        status='invited',
        invited_by=request.user
    )
    messages.success(request, f'Invite sent to {invited_user.username}!')
    return redirect('groups:detail', pk=pk)


@login_required
@require_POST
def respond_invite_view(request, pk):
    """Accept or decline a group invite."""
    membership = get_object_or_404(GroupMember, group_id=pk, user=request.user, status='invited')
    action = request.POST.get('action')
    if action == 'accept':
        membership.status = 'active'
        membership.save()
        messages.success(request, f'You joined {membership.group.name}! 🎉')
        return redirect('groups:detail', pk=pk)
    else:
        membership.delete()
        messages.info(request, f'Invite to {membership.group.name} declined.')
        return redirect('groups:list')


# ── ADMIN ACTIONS (creator only) ──────────────────────────────────────────────

@login_required
@require_POST
def approve_request_view(request, pk, member_id):
    """Approve or reject a join request (admin only)."""
    group = get_object_or_404(Group, pk=pk)
    if not group.is_admin(request.user):
        messages.error(request, 'Not authorised.')
        return redirect('groups:detail', pk=pk)

    membership = get_object_or_404(GroupMember, pk=member_id, group=group, status='pending')
    action = request.POST.get('action')
    if action == 'approve':
        membership.status = 'active'
        membership.save()
        messages.success(request, f'{membership.user.username} approved!')
    else:
        membership.delete()
        messages.info(request, f'{membership.user.username}\'s request rejected.')
    return redirect('groups:detail', pk=pk)


@login_required
@require_POST
@subscription_required
def set_admin_view(request, pk, member_id):
    """Creator promotes/demotes a member to/from admin."""
    group = get_object_or_404(Group, pk=pk)
    if not group.is_creator(request.user):
        messages.error(request, 'Only the group creator can manage admins.')
        return redirect('groups:detail', pk=pk)

    membership = get_object_or_404(GroupMember, pk=member_id, group=group, status='active')
    if membership.role == 'creator':
        messages.error(request, 'Cannot change the creator\'s role.')
        return redirect('groups:detail', pk=pk)

    if membership.role == 'admin':
        membership.role = 'member'
        membership.save()
        messages.info(request, f'{membership.user.username} is no longer an admin.')
    else:
        membership.role = 'admin'
        membership.save()
        messages.success(request, f'{membership.user.username} is now an admin! ⭐')
    return redirect('groups:detail', pk=pk)


@login_required
@require_POST
def remove_member_view(request, pk, member_id):
    """Admin removes a member from the group."""
    group = get_object_or_404(Group, pk=pk)
    if not group.is_admin(request.user):
        messages.error(request, 'Not authorised.')
        return redirect('groups:detail', pk=pk)

    membership = get_object_or_404(GroupMember, pk=member_id, group=group)
    if membership.role == 'creator':
        messages.error(request, 'Cannot remove the group creator.')
        return redirect('groups:detail', pk=pk)
    # Admins can only remove regular members; creator can remove anyone
    if membership.role == 'admin' and not group.is_creator(request.user):
        messages.error(request, 'Only the creator can remove admins.')
        return redirect('groups:detail', pk=pk)

    username = membership.user.username
    membership.delete()
    messages.success(request, f'{username} has been removed from the group.')
    return redirect('groups:detail', pk=pk)


@login_required
def edit_group_view(request, pk):
    group = get_object_or_404(Group, pk=pk)
    if not group.is_creator(request.user):
        messages.error(request, 'Only the creator can edit group settings.')
        return redirect('groups:detail', pk=pk)
    if request.method == 'POST':
        form = GroupEditForm(request.POST, request.FILES, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, 'Group updated!')
            return redirect('groups:detail', pk=pk)
    else:
        form = GroupEditForm(instance=group)
    return render(request, 'groups/edit.html', {'group': group, 'form': form})


@login_required
def delete_group_view(request, pk):
    group = get_object_or_404(Group, pk=pk, creator=request.user)
    if request.method == 'POST':
        name = group.name
        group.delete()
        messages.success(request, f'Group "{name}" deleted.')
        return redirect('groups:list')
    return render(request, 'groups/confirm_delete.html', {'group': group})


@login_required
def delete_post_view(request, pk, post_id):
    group = get_object_or_404(Group, pk=pk)
    post = get_object_or_404(GroupPost, pk=post_id, group=group)
    # Author or admin can delete
    if post.author != request.user and not group.is_admin(request.user):
        messages.error(request, 'Not authorised.')
        return redirect('groups:detail', pk=pk)
    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Post deleted.')
    return redirect('groups:detail', pk=pk)