from django.urls import path
from . import views

urlpatterns = [
    path('reservas/', views.reservas_view, name='reservas'),
    path('administracion/crear-clase/', views.crear_clase_view, name='crear_clase'),
]