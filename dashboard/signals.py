"""
Dashboard signals and helper functions for automatic activity logging.
Import and call these from other apps' views/signals to track user activities.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count

from .models import UserActivity, UserStreak, UserStats, WeeklyLeaderboard, get_week_start

User = get_user_model()


# ─────────────────────────────────────────────
# Public API Functions (call from other apps)
# ─────────────────────────────────────────────

def log_activity(user, activity_type, description, content_object=None, xp_earned=0):
    """
    Central function to log a user activity and update streak/stats.

    Usage:
        from dashboard.signals import log_activity
        from materials.models import Material

        log_activity(request.user, 'material_upload', 'Uploaded "Physics Notes"', material_obj, xp_earned=20)
    """
    activity = UserActivity.log(user, activity_type, description, content_object, xp_earned)

    # Update streak (activity counts as daily activity)
    streak, _ = UserStreak.objects.get_or_create(user=user)
    streak.update_on_activity()

    # Update stats if XP earned
    if xp_earned > 0:
        stats, _ = UserStats.objects.get_or_create(user=user)
        stats.recalculate()

    # Update weekly leaderboard
    update_weekly_leaderboard(user)

    return activity


def log_login_activity(user):
    """Log login activity and update streak."""
    streak, _ = UserStreak.objects.get_or_create(user=user)
    streak.update_on_login()


def update_weekly_leaderboard(user):
    """Update weekly leaderboard entry for user."""
    week_start = get_week_start(timezone.now().date())

    activities = UserActivity.objects.filter(
        user=user,
        created_at__date__gte=week_start,
    )
    xp_earned = activities.aggregate(total=Sum('xp_earned'))['total'] or 0
    activities_count = activities.count()

    WeeklyLeaderboard.objects.update_or_create(
        user=user,
        week_start=week_start,
        defaults={
            'week_end': week_start + timedelta(days=6),
            'xp_earned': xp_earned,
            'activities_count': activities_count,
        }
    )

    # Recalculate ranks for this week
    recalculate_weekly_ranks(week_start)


def recalculate_weekly_ranks(week_start):
    """Recalculate ranks for a given week."""
    entries = WeeklyLeaderboard.objects.filter(week_start=week_start).order_by('-xp_earned', 'user__username')
    for rank, entry in enumerate(entries, 1):
        if entry.rank != rank:
            entry.rank = rank
            entry.save(update_fields=['rank'])


# ─────────────────────────────────────────────
# Signal Receivers (auto-track activities)
# ─────────────────────────────────────────────

# Materials signals
try:
    from materials.models import Material, MaterialPurchase

    @receiver(post_save, sender=Material)
    def material_uploaded(sender, instance, created, **kwargs):
        if created:
            log_activity(
                instance.uploader,
                'material_upload',
                f'Uploaded "{instance.title}"',
                instance,
                xp_earned=20
            )

    @receiver(post_save, sender=MaterialPurchase)
    def material_purchased(sender, instance, created, **kwargs):
        if created and instance.status == 'completed':
            log_activity(
                instance.user,
                'material_download',
                f'Downloaded "{instance.material.title}"',
                instance.material,
                xp_earned=5
            )
except ImportError:
    pass

# Forum signals
try:
    from forum.models import Question, Reply, Like, ReplyLike

    @receiver(post_save, sender=Question)
    def question_posted(sender, instance, created, **kwargs):
        if created:
            log_activity(
                instance.author,
                'question_post',
                f'Asked: {instance.title[:60]}{"..." if len(instance.title) > 60 else ""}',
                instance,
                xp_earned=3
            )

    @receiver(post_save, sender=Reply)
    def reply_posted(sender, instance, created, **kwargs):
        if created:
            log_activity(
                instance.author,
                'question_reply',
                f'Replied to: {instance.question.title[:50]}{"..." if len(instance.question.title) > 50 else ""}',
                instance,
                xp_earned=5
            )

    @receiver(post_save, sender=Like)
    def question_liked(sender, instance, created, **kwargs):
        if created:
            log_activity(
                instance.user,
                'question_like',
                f'Liked question: {instance.question.title[:50]}{"..." if len(instance.question.title) > 50 else ""}',
                instance.question,
                xp_earned=1
            )

    @receiver(post_save, sender=ReplyLike)
    def reply_liked(sender, instance, created, **kwargs):
        if created:
            log_activity(
                instance.user,
                'reply_like',
                f'Liked reply on: {instance.reply.question.title[:50]}{"..." if len(instance.reply.question.title) > 50 else ""}',
                instance.reply,
                xp_earned=1
            )
except ImportError:
    pass

# GROUPS signals
try:
    from GROUPS.models import Group, GroupMember, GroupPost

    @receiver(post_save, sender=Group)
    def group_created(sender, instance, created, **kwargs):
        if created:
            log_activity(
                instance.creator,
                'group_create',
                f'Created study group "{instance.name}"',
                instance,
                xp_earned=10
            )

    @receiver(post_save, sender=GroupMember)
    def group_joined(sender, instance, created, **kwargs):
        if created and instance.status == 'active':
            log_activity(
                instance.user,
                'group_join',
                f'Joined "{instance.group.name}"',
                instance.group,
                xp_earned=5
            )

    @receiver(post_save, sender=GroupPost)
    def group_post(sender, instance, created, **kwargs):
        if created:
            log_activity(
                instance.author,
                'group_post',
                f'Posted in "{instance.group.name}"',
                instance,
                xp_earned=3
            )
except ImportError:
    pass

# Timetable signals
try:
    from timetable.models import Timetable, Course

    @receiver(post_save, sender=Timetable)
    def timetable_created(sender, instance, created, **kwargs):
        if created:
            log_activity(
                instance.user,
                'timetable_create',
                f'Created timetable "{instance.name}"',
                instance,
                xp_earned=5
            )

    @receiver(post_save, sender=Course)
    def course_added(sender, instance, created, **kwargs):
        if created:
            log_activity(
                instance.timetable.user,
                'course_add',
                f'Added "{instance.name}" to {instance.timetable.name}',
                instance,
                xp_earned=2
            )
except ImportError:
    pass

# Quiz signals
try:
    from quiz.models import QuizAttempt

    @receiver(post_save, sender=QuizAttempt)
    def quiz_attempt(sender, instance, created, **kwargs):
        if created:
            log_activity(
                instance.user,
                'quiz_attempt',
                f'Attempted quiz: {instance.quiz.title}',
                instance.quiz,
                xp_earned=10
            )
        elif instance.is_passed and not instance._state.adding:
            # Check if just passed (could use a pre_save signal to track previous state better)
            log_activity(
                instance.user,
                'quiz_pass',
                f'Passed quiz: {instance.quiz.title} ({instance.score}%)',
                instance.quiz,
                xp_earned=20
            )
except ImportError:
    pass