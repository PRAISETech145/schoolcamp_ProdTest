import secrets
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone

from .models import Timetable, Course, TimetableShareRequest, DAYS_OF_WEEK
from .forms import TimetableForm, CourseForm

User = get_user_model()

DAYS_LIST = [
    (0, 'Monday'),
    (1, 'Tuesday'),
    (2, 'Wednesday'),
    (3, 'Thursday'),
    (4, 'Friday'),
    (5, 'Saturday'),
    (6, 'Sunday'),
]


# ─────────────────────────────────────────────
# TIMETABLE LIST / DASHBOARD
# ─────────────────────────────────────────────

@login_required
def timetable_dashboard(request):
    timetables = Timetable.objects.filter(user=request.user)
    active = timetables.filter(is_active=True).first()

    today_index = timezone.now().weekday()
    today_courses = []
    if active:
        today_courses = active.courses.filter(day_of_week=today_index).order_by('start_time')

    now_time = timezone.now().time()
    next_class = None
    if active:
        next_class = active.courses.filter(
            day_of_week=today_index,
            start_time__gt=now_time
        ).order_by('start_time').first()

    context = {
        'timetables': timetables,
        'active_timetable': active,
        'today_courses': today_courses,
        'next_class': next_class,
        'today_name': dict(DAYS_LIST).get(today_index, 'Today'),
        'share_requests': TimetableShareRequest.objects.filter(to_user=request.user, seen=False),
    }
    return render(request, 'timetable/dashboard.html', context)


# ─────────────────────────────────────────────
# TIMETABLE CRUD
# ─────────────────────────────────────────────

@login_required
def timetable_create(request):
    if request.method == 'POST':
        form = TimetableForm(request.POST)
        if form.is_valid():
            timetable = form.save(commit=False)
            timetable.user = request.user
            if request.POST.get('set_active'):
                Timetable.objects.filter(user=request.user).update(is_active=False)
                timetable.is_active = True
            timetable.save()
            messages.success(request, f'Timetable "{timetable.name}" created successfully!')
            return redirect('timetable:detail', pk=timetable.pk)
    else:
        form = TimetableForm()

    return render(request, 'timetable/timetable_form.html', {
        'form': form,
        'title': 'Create Timetable',
        'action': 'Create',
    })


@login_required
def timetable_detail(request, pk):
    timetable = get_object_or_404(Timetable, pk=pk, user=request.user)
    courses_by_day = timetable.get_courses_by_day()

    context = {
        'timetable': timetable,
        'courses_by_day': courses_by_day,
        'days_list': DAYS_LIST,
        'today_index': timezone.now().weekday(),
    }
    return render(request, 'timetable/detail.html', context)


@login_required
def timetable_edit(request, pk):
    timetable = get_object_or_404(Timetable, pk=pk, user=request.user)
    if request.method == 'POST':
        form = TimetableForm(request.POST, instance=timetable)
        if form.is_valid():
            form.save()
            messages.success(request, 'Timetable updated.')
            return redirect('timetable:detail', pk=timetable.pk)
    else:
        form = TimetableForm(instance=timetable)

    return render(request, 'timetable/timetable_form.html', {
        'form': form,
        'timetable': timetable,
        'title': 'Edit Timetable',
        'action': 'Save Changes',
    })


@login_required
def timetable_delete(request, pk):
    timetable = get_object_or_404(Timetable, pk=pk, user=request.user)
    if request.method == 'POST':
        name = timetable.name
        timetable.delete()
        messages.success(request, f'"{name}" deleted.')
        return redirect('timetable:dashboard')
    return render(request, 'timetable/timetable_confirm_delete.html', {'timetable': timetable})


@login_required
def timetable_set_active(request, pk):
    timetable = get_object_or_404(Timetable, pk=pk, user=request.user)
    Timetable.objects.filter(user=request.user).update(is_active=False)
    timetable.is_active = True
    timetable.save()
    messages.success(request, f'"{timetable.name}" is now your active timetable.')
    return redirect('timetable:dashboard')


# ─────────────────────────────────────────────
# COURSE CRUD
# ─────────────────────────────────────────────

@login_required
def course_add(request, timetable_pk):
    timetable = get_object_or_404(Timetable, pk=timetable_pk, user=request.user)

    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            day   = form.cleaned_data['day_of_week']
            start = form.cleaned_data['start_time']
            end   = form.cleaned_data['end_time']

            if timetable.has_clash(day, start, end):
                messages.error(request, '⚠️ Time clash detected! Another course overlaps this slot.')
            else:
                course = form.save(commit=False)
                course.timetable = timetable
                course.save()
                messages.success(request, f'"{course.name}" added to your timetable!')
                return redirect('timetable:detail', pk=timetable.pk)
    else:
        initial = {}
        day_param = request.GET.get('day')
        if day_param is not None:
            initial['day_of_week'] = day_param
        form = CourseForm(initial=initial)

    return render(request, 'timetable/course_form.html', {
        'form': form,
        'timetable': timetable,
        'title': 'Add Course',
        'action': 'Add Course',
    })


@login_required
def course_edit(request, pk):
    course    = get_object_or_404(Course, pk=pk, timetable__user=request.user)
    timetable = course.timetable

    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            day   = form.cleaned_data['day_of_week']
            start = form.cleaned_data['start_time']
            end   = form.cleaned_data['end_time']

            if timetable.has_clash(day, start, end, exclude_id=course.pk):
                messages.error(request, '⚠️ Time clash detected! Another course overlaps this slot.')
            else:
                form.save()
                messages.success(request, f'"{course.name}" updated.')
                return redirect('timetable:detail', pk=timetable.pk)
    else:
        form = CourseForm(instance=course)

    return render(request, 'timetable/course_form.html', {
        'form': form,
        'timetable': timetable,
        'course': course,
        'title': 'Edit Course',
        'action': 'Save Changes',
    })


@login_required
def course_delete(request, pk):
    course    = get_object_or_404(Course, pk=pk, timetable__user=request.user)
    timetable = course.timetable
    if request.method == 'POST':
        name = course.name
        course.delete()
        messages.success(request, f'"{name}" removed.')
        return redirect('timetable:detail', pk=timetable.pk)
    return render(request, 'timetable/course_confirm_delete.html', {
        'course': course,
        'timetable': timetable,
    })


# ─────────────────────────────────────────────
# DAY VIEW (mobile optimized)
# ─────────────────────────────────────────────

@login_required
def day_view(request, pk, day):
    timetable = get_object_or_404(Timetable, pk=pk, user=request.user)
    courses   = timetable.courses.filter(day_of_week=day).order_by('start_time')
    day_name  = dict(DAYS_LIST).get(day, '')

    prev_day = (day - 1) % 7
    next_day = (day + 1) % 7

    return render(request, 'timetable/day_view.html', {
        'timetable': timetable,
        'courses':   courses,
        'day':       day,
        'day_name':  day_name,
        'prev_day':  prev_day,
        'next_day':  next_day,
        'today_index': timezone.now().weekday(),
    })


# ─────────────────────────────────────────────
# SHARING
# ─────────────────────────────────────────────

@login_required
def timetable_share(request, pk):
    timetable = get_object_or_404(Timetable, pk=pk, user=request.user)

    # Load friends using FriendRequest model
    from friends.models import FriendRequest
    from django.db.models import Q
    friends = FriendRequest.get_friends(request.user)

    # Track which friends already received a share request for this timetable
    already_shared_ids = set(
        TimetableShareRequest.objects.filter(
            from_user=request.user,
            timetable=timetable,
        ).values_list('to_user_id', flat=True)
    )

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'generate_link':
            if not timetable.share_token:
                timetable.share_token = secrets.token_urlsafe(32)
            timetable.is_shared = True
            timetable.save()
            messages.success(request, 'Share link generated!')

        elif action == 'revoke_link':
            timetable.share_token = None
            timetable.is_shared   = False
            timetable.save()
            messages.info(request, 'Share link revoked.')

        elif action == 'send_to_friends':
            # Get list of selected friend IDs from checkboxes
            selected_ids = request.POST.getlist('friend_ids')
            if not selected_ids:
                messages.error(request, 'Please select at least one friend.')
            else:
                sent_count = 0
                for uid in selected_ids:
                    try:
                        target = User.objects.get(pk=uid)
                        # Only send if actually a friend (security check)
                        if FriendRequest.are_friends(request.user, target):
                            share_obj, created = TimetableShareRequest.objects.get_or_create(
                                from_user=request.user,
                                to_user=target,
                                timetable=timetable,
                            )
                            # Send notification with link to shared view
                            try:
                                from Notify.services import notify_timetable_share
                                share_url = f'/timetable/shared/{share_obj.pk}/'
                                notify_timetable_share(
                                    recipient=target,
                                    sender=request.user,
                                    timetable_name=timetable.name,
                                    timetable_url=share_url,
                                )
                            except Exception:
                                pass  # Notifications optional — don't break sharing
                            sent_count += 1
                    except User.DoesNotExist:
                        continue

                if sent_count:
                    messages.success(request, f'Timetable shared with {sent_count} friend{"s" if sent_count > 1 else ""}!')
                else:
                    messages.error(request, 'No valid friends selected.')

        return redirect('timetable:share', pk=pk)

    return render(request, 'timetable/share.html', {
        'timetable':        timetable,
        'friends':          friends,
        'already_shared_ids': already_shared_ids,
    })


def timetable_public_view(request, token):
    timetable    = get_object_or_404(Timetable, share_token=token, is_shared=True)
    courses_by_day = timetable.get_courses_by_day()

    return render(request, 'timetable/public_view.html', {
        'timetable':     timetable,
        'courses_by_day': courses_by_day,
        'days_list':     DAYS_LIST,
        'today_index':   timezone.now().weekday(),
    })


# ─────────────────────────────────────────────
# FREE PERIODS FINDER
# ─────────────────────────────────────────────

@login_required
def free_periods(request, pk):
    timetable      = get_object_or_404(Timetable, pk=pk, user=request.user)
    schedule_start = timezone.datetime.strptime('07:00', '%H:%M').time()
    schedule_end   = timezone.datetime.strptime('18:00', '%H:%M').time()

    free_by_day = {}
    for day_idx, day_name in DAYS_LIST:
        courses = list(timetable.courses.filter(day_of_week=day_idx).order_by('start_time'))
        gaps    = []

        if not courses:
            gaps.append({'start': schedule_start, 'end': schedule_end, 'duration': 660})
        else:
            from datetime import datetime
            if courses[0].start_time > schedule_start:
                start_dt = datetime.combine(datetime.today(), schedule_start)
                end_dt   = datetime.combine(datetime.today(), courses[0].start_time)
                mins     = int((end_dt - start_dt).total_seconds() / 60)
                if mins >= 30:
                    gaps.append({'start': schedule_start, 'end': courses[0].start_time, 'duration': mins})

            for i in range(len(courses) - 1):
                start_dt = datetime.combine(datetime.today(), courses[i].end_time)
                end_dt   = datetime.combine(datetime.today(), courses[i + 1].start_time)
                mins     = int((end_dt - start_dt).total_seconds() / 60)
                if mins >= 30:
                    gaps.append({'start': courses[i].end_time, 'end': courses[i + 1].start_time, 'duration': mins})

            if courses[-1].end_time < schedule_end:
                start_dt = datetime.combine(datetime.today(), courses[-1].end_time)
                end_dt   = datetime.combine(datetime.today(), schedule_end)
                mins     = int((end_dt - start_dt).total_seconds() / 60)
                if mins >= 30:
                    gaps.append({'start': courses[-1].end_time, 'end': schedule_end, 'duration': mins})

        free_by_day[day_name] = gaps

    return render(request, 'timetable/free_periods.html', {
        'timetable':  timetable,
        'free_by_day': free_by_day,
    })


# ─────────────────────────────────────────────
# AJAX / API ENDPOINTS
# ─────────────────────────────────────────────

@login_required
def api_courses_json(request, pk):
    timetable = get_object_or_404(Timetable, pk=pk, user=request.user)
    courses   = []
    for course in timetable.courses.all():
        courses.append({
            'id':               course.pk,
            'name':             course.name,
            'code':             course.code,
            'lecturer':         course.lecturer,
            'room':             course.room,
            'day':              course.day_of_week,
            'day_name':         course.get_day_of_week_display(),
            'start_time':       course.start_time.strftime('%H:%M'),
            'end_time':         course.end_time.strftime('%H:%M'),
            'color':            course.color,
            'duration_minutes': course.duration_minutes,
            'notes':            course.notes,
        })
    return JsonResponse({'courses': courses, 'timetable_name': timetable.name})


# ─────────────────────────────────────────────
# SHARED WITH ME
# ─────────────────────────────────────────────

@login_required
def shared_with_me(request):
    """List of all timetables shared with the current user."""
    share_requests = TimetableShareRequest.objects.filter(
        to_user=request.user,
    ).select_related('timetable', 'from_user', 'timetable__user').order_by('-created_at')

    # Mark all as seen
    share_requests.filter(seen=False).update(seen=True)

    return render(request, 'timetable/shared_with_me.html', {
        'share_requests': share_requests,
    })


@login_required
def shared_timetable_view(request, share_id):
    """Read-only view of a timetable shared with the current user."""
    share = get_object_or_404(
        TimetableShareRequest,
        pk=share_id,
        to_user=request.user,
    )
    share.seen = True
    share.save(update_fields=['seen'])

    timetable      = share.timetable
    courses_by_day = timetable.get_courses_by_day()
    today_index    = timezone.now().weekday()
    today_courses  = courses_by_day.get(today_index, [])

    return render(request, 'timetable/shared_timetable_view.html', {
        'share':          share,
        'timetable':      timetable,
        'courses_by_day': courses_by_day,
        'days_list':      DAYS_LIST,
        'today_index':    today_index,
        'today_courses':  today_courses,
        'today_name':     dict(DAYS_LIST).get(today_index, 'Today'),
    })