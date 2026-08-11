from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta, date
import calendar

from .models import (
    UserActivity, UserStreak, UserStats, WeeklyLeaderboard,
    get_week_start
)

User = get_user_model()


# ─────────────────────────────────────────────
# MAIN DASHBOARD
# ─────────────────────────────────────────────

@login_required
def dashboard_home(request):
    """
    Main dashboard view - NeetCode-style overview with streak, stats, recent activity.
    """
    user = request.user

    # Get or create streak
    streak, _ = UserStreak.objects.get_or_create(user=user)

    # Get or create stats
    stats, _ = UserStats.objects.get_or_create(user=user)

    # Recent activities (last 20)
    recent_activities = UserActivity.objects.filter(user=user).select_related('content_type')[:20]

    # This week's stats
    week_start = get_week_start(timezone.now().date())
    week_end = week_start + timedelta(days=6)
    weekly_activities = UserActivity.objects.filter(
        user=user,
        created_at__date__gte=week_start,
        created_at__date__lte=week_end
    )
    weekly_xp = weekly_activities.aggregate(total=Sum('xp_earned'))['total'] or 0
    weekly_count = weekly_activities.count()

    # Weekly rank
    weekly_entry = WeeklyLeaderboard.objects.filter(user=user, week_start=week_start).first()
    weekly_rank = weekly_entry.rank if weekly_entry else None

    # Activity by type for chart
    activity_breakdown = weekly_activities.values('activity_type').annotate(
        count=Count('id'),
        xp=Sum('xp_earned')
    ).order_by('-count')

    total_weekly_xp = sum(item['xp'] or 0 for item in activity_breakdown)

    # Current week day-by-day for heatmap
    week_days = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        day_activities = UserActivity.objects.filter(
            user=user,
            created_at__date=day
        )
        day_xp = day_activities.aggregate(total=Sum('xp_earned'))['total'] or 0
        day_count = day_activities.count()
        week_days.append({
            'date': day,
            'day_name': day.strftime('%a'),
            'is_today': day == timezone.now().date(),
            'is_future': day > timezone.now().date(),
            'xp': day_xp,
            'count': day_count,
            'level': min(day_count // 3 + (1 if day_xp > 0 else 0), 4)  # 0-4 for heatmap intensity
        })

    # Upcoming streak milestones
    next_milestone_days = streak.days_until_milestone

    context = {
        'streak': streak,
        'stats': stats,
        'recent_activities': recent_activities,
        'weekly_xp': weekly_xp,
        'weekly_count': weekly_count,
        'weekly_rank': weekly_rank,
        'weekly_activities': weekly_activities[:10],
        'activity_breakdown': activity_breakdown,
        'total_weekly_xp': total_weekly_xp,
        'week_days': week_days,
        'week_start': week_start,
        'week_end': week_end,
        'next_milestone_days': next_milestone_days,
    }
    return render(request, 'dashboard/home.html', context)


# ─────────────────────────────────────────────
# ACTIVITY FEED
# ─────────────────────────────────────────────

@login_required
def activity_feed(request):
    """
    Full activity feed with filtering by type and date.
    """
    user = request.user
    activities = UserActivity.objects.filter(user=user).select_related('content_type')

    # Filters
    activity_type = request.GET.get('type', '')
    date_from = request.GET.get('from', '')
    date_to = request.GET.get('to', '')

    if activity_type:
        activities = activities.filter(activity_type=activity_type)
    if date_from:
        activities = activities.filter(created_at__date__gte=date_from)
    if date_to:
        activities = activities.filter(created_at__date__lte=date_to)

    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(activities, 30)
    page = request.GET.get('page')
    activities_page = paginator.get_page(page)

    # Activity type choices for filter dropdown
    activity_types = UserActivity.ACTIVITY_TYPES

    context = {
        'activities': activities_page,
        'activity_types': activity_types,
        'active_type': activity_type,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'dashboard/activity_feed.html', context)


# ─────────────────────────────────────────────
# STREAK CALENDAR (GitHub/NeetCode style heatmap)
# ─────────────────────────────────────────────

@login_required
def streak_calendar(request):
    """
    Full year calendar heatmap showing daily activity.
    """
    user = request.user

    # Get target year (default current)
    year = int(request.GET.get('year', timezone.now().year))

    # Get all activities for the year
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)

    activities = UserActivity.objects.filter(
        user=user,
        created_at__date__gte=year_start,
        created_at__date__lte=year_end
    )

    # Build day data dict: {date: {count, xp, level}}
    day_data = {}
    for activity in activities:
        d = activity.created_at.date()
        if d not in day_data:
            day_data[d] = {'count': 0, 'xp': 0}
        day_data[d]['count'] += 1
        day_data[d]['xp'] += activity.xp_earned

    # Calculate level (0-4) for each day
    for d, data in day_data.items():
        data['level'] = min(data['count'] // 3 + (1 if data['xp'] > 0 else 0), 4)

    # Build calendar weeks
    cal = calendar.Calendar(firstweekday=0)  # Monday start
    months_data = []

    for month in range(1, 13):
        month_days = []
        for week in cal.monthdatescalendar(year, month):
            week_data = []
            for d in week:
                if d.year == year:
                    data = day_data.get(d, {'count': 0, 'xp': 0, 'level': 0})
                    current_day_data = {
                        'date': d,
                        'day': d.day,
                        'is_today': d == timezone.now().date(),
                        'is_current_month': d.month == month,
                        'count': data.get('count', 0),
                        'xp': data.get('xp', 0),
                        'level': data.get('level', 0),
                    }
                else:
                    current_day_data = {
                        'date': d,
                        'day': d.day,
                        'is_current_month': False,
                        'count': 0,
                        'xp': 0,
                        'level': 0,
                    }
                week_data.append(current_day_data)
            month_days.append(week_data)

        months_data.append({
            'month': month,
            'month_name': date(year, month, 1).strftime('%B'),
            'weeks': month_days,
        })

    # Streak info
    streak, _ = UserStreak.objects.get_or_create(user=user)

    prev_year = year - 1
    next_year = year + 1

    context = {
        'year': year,
        'prev_year': prev_year,
        'next_year': next_year,
        'months': months_data,
        'streak': streak,
        'total_active_days': len([d for d in day_data.values() if d['count'] > 0]),
        'total_xp_year': sum(d['xp'] for d in day_data.values()),
    }
    return render(request, 'dashboard/streak_calendar.html', context)


# ─────────────────────────────────────────────
# DETAILED STATS
# ─────────────────────────────────────────────

@login_required
def stats_detail(request):
    """
    Detailed statistics page with charts and breakdowns.
    """
    user = request.user

    # Get or create stats
    stats, _ = UserStats.objects.get_or_create(user=user)

    # All-time stats from activities
    all_activities = UserActivity.objects.filter(user=user)

    # By activity type
    type_stats = all_activities.values('activity_type').annotate(
        count=Count('id'),
        xp=Sum('xp_earned')
    ).order_by('-count')

    # By month (last 12 months)
    monthly_stats = []
    for i in range(12):
        month_start = (timezone.now().replace(day=1) - timedelta(days=30*i)).replace(day=1)
        if i == 0:
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        else:
            prev_month_start = (timezone.now().replace(day=1) - timedelta(days=30*(i-1))).replace(day=1)
            month_end = prev_month_start - timedelta(days=1)

        month_activities = all_activities.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=month_end
        )
        monthly_stats.append({
            'month': month_start.strftime('%b %Y'),
            'month_start': month_start,
            'count': month_activities.count(),
            'xp': month_activities.aggregate(total=Sum('xp_earned'))['total'] or 0,
        })
    monthly_stats.reverse()  # Chronological order

    # XP progression over time (cumulative)
    xp_progression = []
    cumulative = 0
    for ms in monthly_stats:
        cumulative += ms['xp']
        xp_progression.append({
            'month': ms['month'],
            'cumulative_xp': cumulative,
        })

    # Top activity days
    top_days = UserActivity.objects.filter(user=user).extra(
        select={'activity_date': 'date(created_at)'}
    ).values('activity_date').annotate(
        count=Count('id'),
        xp=Sum('xp_earned')
    ).order_by('-count')[:10]

    # Streak
    streak, _ = UserStreak.objects.get_or_create(user=user)

    context = {
        'stats': stats,
        'type_stats': type_stats,
        'monthly_stats': monthly_stats,
        'xp_progression': xp_progression,
        'top_days': top_days,
        'streak': streak,
    }
    return render(request, 'dashboard/stats_detail.html', context)


# ─────────────────────────────────────────────
# LEADERBOARDS
# ─────────────────────────────────────────────

@login_required
def leaderboard(request):
    """
    Weekly and all-time leaderboards.
    """
    # Current week
    week_start = get_week_start(timezone.now().date())
    weekly_entries = WeeklyLeaderboard.objects.filter(
        week_start=week_start
    ).select_related('user').order_by('rank')[:50]

    # All-time top users by XP
    top_users = UserStats.objects.select_related('user').order_by('-total_xp')[:50]

    # User's position
    user_weekly = WeeklyLeaderboard.objects.filter(
        user=request.user, week_start=week_start
    ).first()
    user_alltime = UserStats.objects.filter(user=request.user).first()

    # Streak leaderboard
    streak_leaders = UserStreak.objects.select_related('user').order_by(
        '-current_streak', '-longest_streak'
    )[:20]

    context = {
        'week_start': week_start,
        'weekly_entries': weekly_entries,
        'top_users': top_users,
        'user_weekly': user_weekly,
        'user_alltime': user_alltime,
        'streak_leaders': streak_leaders,
    }
    return render(request, 'dashboard/leaderboard.html', context)


# ─────────────────────────────────────────────
# USER PROFILE DASHBOARD (Public view)
# ─────────────────────────────────────────────

@login_required
def user_profile_dashboard(request, username):
    """
    Public view of another user's dashboard (limited info).
    """
    profile_user = get_object_or_404(User, username=username)

    streak = UserStreak.objects.filter(user=profile_user).first()
    stats = UserStats.objects.filter(user=profile_user).first()
    recent_activities = UserActivity.objects.filter(user=profile_user).select_related('content_type')[:15]

    # Only show public stats
    context = {
        'profile_user': profile_user,
        'streak': streak,
        'stats': stats,
        'recent_activities': recent_activities,
        'is_own': profile_user == request.user,
    }
    return render(request, 'dashboard/user_profile.html', context)


# ─────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────

@login_required
def api_streak_status(request):
    """API endpoint for streak status (for navbar badge)."""
    streak, _ = UserStreak.objects.get_or_create(user=request.user)

    return JsonResponse({
        'current_streak': streak.current_streak,
        'longest_streak': streak.longest_streak,
        'total_active_days': streak.total_active_days,
        'last_activity_date': streak.last_activity_date.isoformat() if streak.last_activity_date else None,
        'status': streak.get_streak_status(),
        'has_freeze': streak.has_freeze,
        'milestone_days': streak.days_until_milestone(),
    })


@login_required
def api_weekly_progress(request):
    """API for weekly progress widget."""
    user = request.user
    week_start = get_week_start(timezone.now().date())

    daily_data = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        activities = UserActivity.objects.filter(user=user, created_at__date=day)
        xp = activities.aggregate(total=Sum('xp_earned'))['total'] or 0
        count = activities.count()

        daily_data.append({
            'date': day.isoformat(),
            'day_name': day.strftime('%a'),
            'is_today': day == timezone.now().date(),
            'xp': xp,
            'count': count,
        })

    weekly_entry = WeeklyLeaderboard.objects.filter(user=user, week_start=week_start).first()

    return JsonResponse({
        'week_start': week_start.isoformat(),
        'daily': daily_data,
        'total_xp': sum(d['xp'] for d in daily_data),
        'total_activities': sum(d['count'] for d in daily_data),
        'rank': weekly_entry.rank if weekly_entry else None,
        'xp_earned': weekly_entry.xp_earned if weekly_entry else 0,
    })


@login_required
def api_recent_activities(request):
    """API for recent activities widget."""
    limit = int(request.GET.get('limit', 10))
    activities = UserActivity.objects.filter(user=request.user).select_related('content_type')[:limit]

    data = []
    for a in activities:
        data.append({
            'type': a.activity_type,
            'description': a.description,
            'xp_earned': a.xp_earned,
            'created_at': a.created_at.isoformat(),
            'time_ago': _time_ago(a.created_at),
        })

    return JsonResponse({'activities': data})


def _time_ago(dt):
    """Helper to format datetime as 'X time ago'."""
    now = timezone.now()
    diff = now - dt

    if diff.days > 0:
        return f"{diff.days}d ago"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours}h ago"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes}m ago"
    else:
        return "just now"