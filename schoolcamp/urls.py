from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path("social-auth/", include("allauth.urls")),
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/forum/'), name='home'),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('forum/', include('forum.urls', namespace='forum')),
    path('Group/', include('GROUPS.urls', namespace='groups')),
    path('friends/', include('friends.urls', namespace='friends')),
    path('quiz/', include('quiz.urls', namespace='quiz')),
    path('materials/', include('materials.urls', namespace='materials')),
    path('chat/', include('chat.urls', namespace='chat')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
    path('payment/', include('payment.urls', namespace='payment')),
    path('GCE/',include('GCE.urls',namespace='GCE')),
    path('timetable/', include('timetable.urls', namespace='timetable')),
    path('legal/', include('legal.urls', namespace='legal')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)