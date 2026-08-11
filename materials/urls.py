from django.urls import path
from . import views

app_name = 'materials'

urlpatterns = [
    path('', views.materials_list_view, name='list'),
    path('upload/', views.upload_material_view, name='upload'),
    path('mine/', views.my_materials_view, name='my_materials'),
    path('<int:pk>/', views.material_detail_view, name='detail'),
    path('<int:pk>/download/', views.download_material_view, name='download'),
    path('<int:pk>/delete/', views.delete_material_view, name='delete'),
    path('maths/',views.Maths_view,name='maths'),
    path('physics/',views.physics_view,name='physics'),
    path('chemistry/',views.chemistry_view,name='chemistry'),
    path('biology/',views.Biology_view,name='biology'),
    path('computerScience/',views.computerScience_view,name='CSC'),
    path('french/',views.french_view,name='french'),
    path('economics/',views.Economics_view,name='economics'),
]
