from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum


class UserActivity(models.Model):
    """
    Tracks all user activities across the platform for the activity feed and streak calculation.
    """
    ACTIVITY_TYPES = [
        ('material_upload', 'Material Upload'),
        ('material_download', 'Material Download'),
        ('material_view', 'Material View'),
        ('quiz_attempt', 'Quiz Attempt'),
        ('quiz_pass', 'Quiz Passed'),
        ('question_post', 'Question Posted'),
        ('question_reply', 'Reply Posted'),
        ('question_like', 'Question Liked'),
        ('reply_like', 'Reply Liked'),
        ('answer_accepted', 'Answer Accepted'),
        ('timetable_create', 'Timetable Created'),
        ('timetable_update', 'Timetable Updated'),
        ('course_add', 'Course Added'),
        ('group_create', 'Study Group Created'),
        ('group_join', 'Study Group Joined'),
        ('group_post', 'Group Post'),
        ('login', 'Login'),
        ('xp_earned', 'XP Earned'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPES)
    description = models.CharField(max_length=255)

    # Generic foreign key to link to any model
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    # XP awarded for this activity
    xp_earned = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User Activity'
        verbose_name_plural = 'User Activities'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['user', 'activity_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.activity_type} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    @classmethod
    def log(cls, user, activity_type, description, content_object=None, xp_earned=0):
        """Helper method to log an activity."""
        data = {
            'user': user,
            'activity_type': activity_type,
            'description': description,
            'xp_earned': xp_earned,
        }
        if content_object:
            data['content_type'] = ContentType.objects.get_for_model(content_object)
            data['object_id'] = content_object.pk
        return cls.objects.create(**data)


class UserStreak(models.Model):
    """
    Tracks user's daily login/activity streak (NeetCode-style).
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='streak'
    )
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    last_login_date = models.DateField(null=True, blank=True)
    total_active_days = models.PositiveIntegerField(default=0)

    # Freeze streak (streak protection - can be earned or purchased)
    has_freeze = models.BooleanField(default=False)
    freeze_expires_at = models.DateTimeField(null=True, blank=True)
    freezes_used = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'User Streak'
        verbose_name_plural = 'User Streaks'

    def __str__(self):
        return f"{self.user.username} - {self.current_streak} days 🔥"

    def update_on_activity(self):
        """Update streak when user performs any activity."""
        today = timezone.now().date()

        if self.last_activity_date is None:
            # First activity ever
            self.current_streak = 1
            self.longest_streak = 1
            self.total_active_days = 1
            self.last_activity_date = today
        elif self.last_activity_date == today:
            # Already active today, no change
            pass
        elif self.last_activity_date == today - timedelta(days=1):
            # Consecutive day
            self.current_streak += 1
            if self.current_streak > self.longest_streak:
                self.longest_streak = self.current_streak
            self.total_active_days += 1
            self.last_activity_date = today
        else:
            # Streak broken - check if freeze is active
            if self.has_freeze and self.freeze_expires_at and timezone.now() < self.freeze_expires_at:
                # Freeze active - streak preserved but not incremented
                self.has_freeze = False
                self.freeze_expires_at = None
                # Don't increment streak, but don't reset it either
            else:
                # Streak broken
                self.current_streak = 1
                self.total_active_days += 1
                self.last_activity_date = today

        self.save()
        return self.current_streak

    def update_on_login(self):
        """Update streak on login (separate from general activity)."""
        today = timezone.now().date()

        if self.last_login_date is None:
            self.last_login_date = today
            self.save()
        elif self.last_login_date < today:
            self.last_login_date = today
            self.save()
        # If already logged in today, no change

    def get_streak_status(self):
        """Get human-readable streak status."""
        if self.current_streak == 0:
            return "Start your streak today!"
        elif self.current_streak == 1:
            return "1 day streak - keep going! 🌱"
        elif self.current_streak < 7:
            return f"{self.current_streak} day streak - building momentum! 🔥"
        elif self.current_streak < 30:
            return f"{self.current_streak} day streak - on fire! 🔥"
        elif self.current_streak < 100:
            return f"{self.current_streak} day streak - unstoppable! 💪"
        else:
            return f"{self.current_streak} day streak - LEGENDARY! 🏆"

    @property
    def days_until_milestone(self):
        """Days until next streak milestone."""
        milestones = [7, 14, 30, 60, 100, 200, 365, 500, 1000]
        for m in milestones:
            if self.current_streak < m:
                return m - self.current_streak
        return 0

    @property
    def get_progress_to_milestone(self):
        """Progress percentage to next milestone."""
        milestones = [7, 14, 30, 60, 100, 200, 365, 500, 1000]
        prev = 0
        for m in milestones:
            if self.current_streak < m:
                if prev == 0:
                    return int((self.current_streak / m) * 100)
                return int(((self.current_streak - prev) / (m - prev)) * 100)
            prev = m
        return 100

    @property
    def progress_to_milestone(self):
        return self.get_progress_to_milestone

    @property
    def milestones_achieved(self):
        """List of milestones user has reached."""
        milestones = [7, 14, 30, 60, 100, 200, 365, 500, 1000]
        achieved = []
        for m in milestones:
            if self.current_streak >= m or self.longest_streak >= m:
                achieved.append(m)
        return achieved


class UserStats(models.Model):
    """
    Aggregated statistics for a user (for leaderboards and profile).
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stats'
    )
    total_xp = models.PositiveIntegerField(default=0)
    total_materials_uploaded = models.PositiveIntegerField(default=0)
    total_materials_downloaded = models.PositiveIntegerField(default=0)
    total_quizzes_taken = models.PositiveIntegerField(default=0)
    total_quizzes_passed = models.PositiveIntegerField(default=0)
    total_questions_asked = models.PositiveIntegerField(default=0)
    total_replies_posted = models.PositiveIntegerField(default=0)
    total_answers_accepted = models.PositiveIntegerField(default=0)
    total_groups_created = models.PositiveIntegerField(default=0)
    total_groups_joined = models.PositiveIntegerField(default=0)

    # Weekly stats reset
    weekly_xp = models.PositiveIntegerField(default=0)
    weekly_rank = models.PositiveIntegerField(default=0)
    week_start = models.DateField(null=True, blank=True)

    # All-time rank
    global_rank = models.PositiveIntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Stats'
        verbose_name_plural = 'User Stats'

    def __str__(self):
        return f"{self.user.username} - {self.total_xp} XP"

    def recalculate(self):
        """Recalculate all stats from activities and related models."""
        # This would query various models to compute stats
        # For now, we'll use xp_points from User model and activity counts
        from accounts.models import User
        user = User.objects.get(pk=self.user.pk)
        self.total_xp = user.xp_points

        # Count activities by type
        activities = UserActivity.objects.filter(user=self.user)
        self.total_materials_uploaded = activities.filter(activity_type='material_upload').count()
        self.total_materials_downloaded = activities.filter(activity_type='material_download').count()
        self.total_quizzes_taken = activities.filter(activity_type='quiz_attempt').count()
        self.total_quizzes_passed = activities.filter(activity_type='quiz_pass').count()
        self.total_questions_asked = activities.filter(activity_type='question_post').count()
        self.total_replies_posted = activities.filter(activity_type='question_reply').count()
        self.total_answers_accepted = activities.filter(activity_type='answer_accepted').count()

        self.save()


class WeeklyLeaderboard(models.Model):
    """
    Weekly leaderboard entries for competitive motivation.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='weekly_leaderboard_entries'
    )
    week_start = models.DateField()
    week_end = models.DateField()
    xp_earned = models.PositiveIntegerField(default=0)
    activities_count = models.PositiveIntegerField(default=0)
    rank = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'week_start')
        ordering = ['-xp_earned', 'user__username']
        verbose_name = 'Weekly Leaderboard Entry'
        verbose_name_plural = 'Weekly Leaderboard Entries'

    def __str__(self):
        return f"Week {self.week_start} - {self.user.username}: #{self.rank} ({self.xp_earned} XP)"


def get_week_start(date):
    """Get Monday (week start) for a given date."""
    return date - timedelta(days=date.weekday())