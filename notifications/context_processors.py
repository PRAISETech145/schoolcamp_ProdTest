from .models import Notification

def unread_notifications(request):
    """
    Context processor to add unread notification count to all templates.
    """
    if request.user.is_authenticated:
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return {'unread_notifications_count': count}
    return {'unread_notifications_count': 0}