from django.urls import path
from . import views

app_name = 'actividad'

urlpatterns = [
    path('admin/', views.admin_actividades, name='admin_actividades'),
    path('admin/crear/', views.crear_actividad, name='crear_actividad'),
    path('admin/<int:actividad_id>/modificar/', views.modificar_actividad, name='modificar_actividad'),
    path('admin/<int:actividad_id>/eliminar/', views.eliminar_actividad, name='eliminar_actividad'),
]
