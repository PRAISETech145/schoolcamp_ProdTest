from django.urls import path
from . import views

app_name = 'GCE'

urlpatterns = [
    path('', views.material_list,name='list'),
    path('<int:pk>/',views.material_detail,name='detail'),
    path('<int:pk>/buy/',views.initiate_purchase,name='buy'),
    path('purchase/<int:pk>/pending/',views.purchase_pending,name='purchase_pending'),
    path('purchase/<int:pk>/status/', views.purchase_status, name='purchase_status'),
    path('purchase/<int:pk>/confirm/',views.confirm_purchase_dev,name='confirm_dev'),  # DEV ONLY
    path('<int:pk>/ready/',views.download_ready,name='download_ready'),
    path('download/<uuid:token>/',views.secure_download,name='secure_download'),
    path('webhook/',views.payment_webhook,name='webhook'),
    path('solution/<int:solution_pk>/buy/',             views.initiate_solution_purchase,    name='buy_solution'),
    path('solution/purchase/<int:pk>/pending/',         views.solution_purchase_pending,     name='solution_purchase_pending'),
    path('solution/purchase/<int:pk>/status/',          views.solution_purchase_status,      name='solution_purchase_status'),
    path('solution/<int:solution_pk>/download/',        views.solution_download_ready,       name='solution_download'),
    path('solution/webhook/',                           views.solution_payment_webhook,      name='solution_webhook'),
    path('solution/purchase/<int:pk>/confirm-dev/',     views.confirm_solution_purchase_dev, name='confirm_solution_purchase_dev'),
]


