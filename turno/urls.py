from django.urls import path
from . import views

urlpatterns = [
    path('clases/', views.lista_clases, name='lista_clases'),
    path('api/calendario/', views.calendario_api, name='calendario_api'),
    path('clases/<int:clase_id>/', views.ver_clase, name='ver_clase'),
    path('clases/<int:clase_id>/reservar/', views.pedir_turno, name='pedir_turno_detalle'),
    path('reservas/', views.mis_turnos, name='reservas'),
    path('reservas/<int:reserva_id>/', views.detalle_reserva, name='detalle_reserva'),
    path('reservas/<int:reserva_id>/exitosa/', views.reserva_exitosa, name='reserva_exitosa'),
    path('reservas/cancelar/<int:reserva_id>/', views.cancelar_reserva, name='cancelar_reserva'),

    # Admin de clases
    path('admin/clases/', views.admin_clases, name='admin_clases'),
    path('admin/clases/crear/', views.crear_clase, name='crear_clase'),
    path('admin/clases/<int:clase_id>/modificar/', views.modificar_clase, name='modificar_clase'),
    path('admin/clases/<int:clase_id>/cancelar/', views.cancelar_clase, name='cancelar_clase'),
    path('admin/clases/<int:clase_id>/detalle/', views.detalle_clase, name='detalle_clase'),

    # QR y asistencia
    path('api/qr/validar/', views.validar_qr_api, name='validar_qr_api'),
    path('admin/escanear-qr/', views.escanear_qr, name='escanear_qr'),
    path('admin/reserva/<int:reserva_id>/pago-efectivo/', views.registrar_pago_efectivo, name='registrar_pago_efectivo'),
]