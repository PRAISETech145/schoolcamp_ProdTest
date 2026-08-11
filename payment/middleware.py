from django.shortcuts import redirect
from django.urls import reverse, resolve
from django.contrib import messages


# URLs that are always accessible (no subscription needed)
EXEMPT_URL_NAMES = {
    'payment:wall',
    'payment:initiate',
    'payment:pending',
    'payment:status',
    'payment:confirm',
    'payment:success',
    'payment:failed',
    'payment:webhook',
    'payment:subscription',
    'accounts:login',
    'accounts:logout',
    'accounts:register',
    'admin:index',
}

EXEMPT_URL_PREFIXES = [
    '/admin/',
    '/payment/',
    '/accounts/login',
    '/accounts/logout',
    '/accounts/register',
    '/static/',
    '/media/',
]


class SubscriptionMiddleware:
    """
    Middleware that checks subscription status on every request.
    Redirects to payment wall if the user's trial has expired.

    To enable, add to settings.py MIDDLEWARE list:
        'payment.middleware.SubscriptionMiddleware',

    Place it AFTER 'django.contrib.auth.middleware.AuthenticationMiddleware'.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._should_check(request):
            from payment.models import Subscription
            try:
                sub = request.user.subscription
            except Subscription.DoesNotExist:
                sub, _ = Subscription.objects.get_or_create(user=request.user)

            if not sub.is_active:
                messages.warning(
                    request,
                    '⏰ Your free trial has expired. Subscribe to continue.'
                )
                return redirect(reverse('payment:wall'))

        return self.get_response(request)

    def _should_check(self, request):
        # Guard: ASGI or missing auth middleware means request.user may not exist yet
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return False

        path = request.path_info

        # Skip exempt URL prefixes
        for prefix in EXEMPT_URL_PREFIXES:
            if path.startswith(prefix):
                return False

        # Skip exempt named URLs
        try:
            resolved = resolve(path)
            url_name = f"{resolved.namespace}:{resolved.url_name}" if resolved.namespace else resolved.url_name
            if url_name in EXEMPT_URL_NAMES:
                return False
        except Exception:
            return False

        return True