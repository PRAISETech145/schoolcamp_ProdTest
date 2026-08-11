from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'notifications/list.html'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).order_by('-created_at')


@login_required
@require_POST
def mark_as_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.mark_as_read()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    messages.success(request, 'Notification marked as read.')
    return redirect('notifications:list')


@login_required
@require_POST
def mark_all_as_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    messages.success(request, 'All notifications marked as read.')
    return redirect('notifications:list')


@login_required
def unread_count(request):
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'count': count})
    return redirect('notifications:list')


@login_required
@require_POST
def delete_notification(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.delete()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    messages.success(request, 'Notification deleted.')
    return redirect('notifications:list')