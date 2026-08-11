from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings


DAYS_OF_WEEK = [
    (0, 'Monday'),
    (1, 'Tuesday'),
    (2, 'Wednesday'),
    (3, 'Thursday'),
    (4, 'Friday'),
    (5, 'Saturday'),
    (6, 'Sunday'),
]

SUBJECT_COLORS = [
    ('#4CAF50', 'Green'),
    ('#2196F3', 'Blue'),
    ('#F44336', 'Red'),
    ('#FF9800', 'Orange'),
    ('#9C27B0', 'Purple'),
    ('#00BCD4', 'Cyan'),
    ('#E91E63', 'Pink'),
    ('#795548', 'Brown'),
    ('#607D8B', 'Blue Grey'),
    ('#FFEB3B', 'Yellow'),
]

SEMESTER_CHOICES = [
    ('1', 'Semester 1'),
    ('2', 'Semester 2'),
    ('annual', 'Annual'),
]


class Timetable(models.Model):
    """A student's timetable for a given academic period."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='timetables')
    name = models.CharField(max_length=100, default='My Timetable')
    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES, default='1')
    academic_year = models.CharField(max_length=20, default='2024/2025')
    is_active = models.BooleanField(default=True)
    is_shared = models.BooleanField(default=False)
    share_token = models.CharField(max_length=64, blank=True, null=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.name} ({self.get_semester_display()})"

    def get_courses_by_day(self):
        """Return courses grouped by day of week."""
        grouped = {i: [] for i in range(7)}
        for course in self.courses.all().order_by('day_of_week', 'start_time'):
            grouped[course.day_of_week].append(course)
        return grouped

    def has_clash(self, day, start_time, end_time, exclude_id=None):
        """Check if a given time slot clashes with existing courses."""
        qs = self.courses.filter(day_of_week=day)
        if exclude_id:
            qs = qs.exclude(id=exclude_id)
        for course in qs:
            if start_time < course.end_time and end_time > course.start_time:
                return True
        return False


class Course(models.Model):
    """A single course/class entry in a timetable."""
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name='courses')
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20, blank=True)
    lecturer = models.CharField(max_length=100, blank=True)
    room = models.CharField(max_length=50, blank=True)
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    color = models.CharField(max_length=7, choices=SUBJECT_COLORS, default='#4CAF50')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        return f"{self.name} ({self.get_day_of_week_display()} {self.start_time}–{self.end_time})"

    @property
    def duration_minutes(self):
        start = timezone.datetime.combine(timezone.datetime.today(), self.start_time)
        end = timezone.datetime.combine(timezone.datetime.today(), self.end_time)
        return int((end - start).total_seconds() / 60)

    @property
    def duration_display(self):
        mins = self.duration_minutes
        hours = mins // 60
        remaining = mins % 60
        if hours and remaining:
            return f"{hours}h {remaining}m"
        elif hours:
            return f"{hours}h"
        return f"{remaining}m"


class TimetableShareRequest(models.Model):
    """Track share requests between students."""
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_share_requests')
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_share_requests')
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    seen = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.from_user} → {self.to_user}: {self.timetable.name}"
