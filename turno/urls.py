from django.urls import path
from . import views

urlpatterns = [
    path('clases/', views.lista_clases, name='lista_clases'),
    path('clases/<int:clase_id>/', views.ver_clase, name='ver_clase'),
    path('clases/<int:clase_id>/reservar/', views.pedir_turno, name='pedir_turno_detalle'),
    path('reservas/', views.mis_turnos, name='reservas'),
    path('reservas/<int:reserva_id>/exitosa/', views.reserva_exitosa, name='reserva_exitosa'),
    path('reservas/cancelar/<int:reserva_id>/', views.cancelar_reserva, name='cancelar_reserva'),

    # Admin de clases
    path('admin/clases/', views.admin_clases, name='admin_clases'),
    path('admin/clases/crear/', views.crear_clase, name='crear_clase'),
    path('admin/clases/<int:clase_id>/modificar/', views.modificar_clase, name='modificar_clase'),
    path('admin/clases/<int:clase_id>/cancelar/', views.cancelar_clase, name='cancelar_clase'),
    path('admin/clases/<int:clase_id>/detalle/', views.detalle_clase, name='detalle_clase'),
]