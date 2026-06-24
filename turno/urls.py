from django.urls import path
from . import views



urlpatterns = [
    path('clases/', views.lista_clases, name='lista_clases'),
    path('api/calendario/', views.calendario_api, name='calendario_api'),
    path('clases/<int:clase_id>/', views.ver_clase, name='ver_clase'),
    path('clases/<int:clase_id>/reservar/', views.pedir_turno, name='pedir_turno_detalle'),
    path('clases/<int:clase_id>/salir-espera/', views.salir_lista_espera, name='salir_lista_espera'),
    path('clases/<int:clase_id>/aceptar-cupo/', views.aceptar_cupo, name='aceptar_cupo'),
    path('reservas/', views.mis_turnos, name='reservas'),
    path('reservas/<int:reserva_id>/', views.detalle_reserva, name='detalle_reserva'),
    path('reservas/<int:reserva_id>/exitosa/', views.reserva_exitosa, name='reserva_exitosa'),
    path('reservas/cancelar/<int:reserva_id>/', views.cancelar_reserva, name='cancelar_reserva'),
    path('reservas/<int:reserva_id>/opciones-reembolso/', views.opciones_reembolso, name='opciones_reembolso'),

    # Admin de clases
    path('admin/clases/', views.admin_clases, name='admin_clases'),
    path('admin/clases/crear/', views.crear_clase, name='crear_clase'),
    path('admin/clases/<int:clase_id>/modificar/', views.modificar_clase, name='modificar_clase'),
    path('admin/clases/<int:clase_id>/cancelar/', views.cancelar_clase, name='cancelar_clase'),
    path('admin/clases/<int:clase_id>/detalle/', views.detalle_clase, name='detalle_clase'),

    path('admin/clases/<int:clase_id>/presentes/', views.lista_presentes_clase, name='lista_presentes_clase'),

    # QR y asistencia
    path('api/qr/validar/', views.validar_qr_api, name='validar_qr_api'),
    path('admin/escanear-qr/', views.escanear_qr, name='escanear_qr'),
    path('admin/reserva/<int:reserva_id>/pago-presencial/', views.registrar_pago_presencial, name='registrar_pago_presencial'),
    path('asistencia/<uuid:qr_uuid>/', views.registrar_asistencia_view, name='asistencia_qr')


    # Registrar asistencia manual
    path('admin/reserva/<int:reserva_id>/asistencia-manual/', views.registrar_asistencia_view, name='registrar_asistencia_manual'),
    
    # Abono mensual
    path('abono/abonar/', views.abonar_mes, name='abonar_mes'),
    path('abono/hacerse-abonado/', views.hacerse_abonado, name='hacerse_abonado'),
    path('abono/exito/', views.abono_exito, name='abono_exito'),
    path('abono/fallo/', views.abono_fallo, name='abono_fallo'),
    path('abono/pendiente/', views.abono_pendiente, name='abono_pendiente'),
        # Nuevas funcionalidades de turno fijo
    path('abono/nuevo-turno-fijo/', views.abonar_nuevo_turno_fijo, name='abonar_nuevo_turno_fijo'),
    path('abono/ver-turnos-fijos/', views.ver_turnos_fijos, name='ver_turnos_fijos'),
    path('admin/cliente/<int:user_id>/pago-turno-fijo/', views.registrar_pago_abono_admin, name='registrar_pago_abono_admin'),
]