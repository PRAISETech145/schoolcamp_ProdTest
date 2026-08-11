from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

FREE_TRIAL_DAYS = 25
SUBSCRIPTION_AMOUNT = 200  # XAF (CFA Francs)


class Subscription(models.Model):
    STATUS_CHOICES = [
        ('trial', 'Free Trial'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('pending', 'Payment Pending'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trial')
    trial_start = models.DateTimeField(default=timezone.now)
    trial_end = models.DateTimeField(null=True, blank=True)
    paid_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.trial_end:
            self.trial_end = self.trial_start + timedelta(days=FREE_TRIAL_DAYS)  # For testing, set to 2 minutes. Change to days=FREE_TRIAL_DAYS for production.
        super().save(*args, **kwargs)

    @property
    def is_trial_expired(self):
        return timezone.now() > self.trial_end

    @property
    def is_active(self):
        if self.status == 'trial' and not self.is_trial_expired:
            return True
        if self.status == 'active' and self.paid_until and timezone.now() < self.paid_until:
            return True
        return False

    @property
    def days_left_in_trial(self):
        if self.status == 'trial' and not self.is_trial_expired:
            delta = self.trial_end - timezone.now()
            return max(0, delta.days)
        return 0

    def __str__(self):
        return f"{self.user.username} — {self.status}"


class Payment(models.Model):
    PROVIDER_CHOICES = [
        ('mtn', 'MTN Mobile Money'),
        ('orange', 'Orange Money'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    phone_number = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=10, decimal_places=0, default=SUBSCRIPTION_AMOUNT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reference = models.CharField(max_length=100, unique=True)
    operator_reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} — {self.provider} — {self.status}"
    
