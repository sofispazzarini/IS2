from django.urls import path
from . import views

urlpatterns = [

    path('reservas/', views.reservas_view, name='reservas'),
    path('administracion/crear-clase/', views.crear_clase_view, name='crear_clase'),
    path('administracion/clases/', views.lista_clases_admin, name='lista_clases_admin'),
    path('administracion/clases/editar/<int:pk>/', views.editar_clase_view, name='editar_clase'),
    path('administracion/clases/cancelar/<int:pk>/', views.cancelar_clase_view, name='cancelar_clase'),

    path('administracion/clases/<int:clase_id>/inscriptos/', views.ver_inscriptos_view, name='ver_inscriptos'),
    path('administracion/reserva/<int:reserva_id>/asistencia/', views.registrar_asistencia_view, name='registrar_asistencia'),
    
    path('clases/', views.lista_clases, name='lista_clases'),
    path('clases/<int:clase_id>/reservar/', views.pedir_turno, name='pedir_turno_detalle'),
    path('reservas/<int:reserva_id>/exitosa/', views.reserva_exitosa, name='reserva_exitosa'),
    path('reservas/cancelar/<int:reserva_id>/', views.cancelar_reserva, name='cancelar_reserva'),
]