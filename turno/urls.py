from django.urls import path
from . import views

urlpatterns = [
    path('clases/', views.lista_clases, name='lista_clases'),
    # Esta ruta maneja tanto ver el detalle como apretar el botón de confirmar
    path('clases/<int:clase_id>/reservar/', views.pedir_turno, name='pedir_turno_detalle'),
    path('reservas/<int:reserva_id>/exitosa/', views.reserva_exitosa, name='reserva_exitosa'),
    path('reservas/cancelar/<int:reserva_id>/', views.cancelar_reserva, name='cancelar_reserva')
    ]