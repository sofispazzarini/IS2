from django.urls import path
from . import views

urlpatterns = [
    path('reservas/', views.reservas_view, name='reservas'),
    path('administracion/crear-clase/', views.crear_clase_view, name='crear_clase'),
    path('administracion/clases/', views.lista_clases_admin, name='lista_clases_admin'),
    path('administracion/clases/editar/<int:pk>/', views.editar_clase_view, name='editar_clase'),
    path('administracion/clases/cancelar/<int:pk>/', views.cancelar_clase_view, name='cancelar_clase'),
]