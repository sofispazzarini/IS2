from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction

from .models import Reserva, Asistencia


class ResultadoValidacionQR:
    def __init__(self, exito, mensaje, reserva=None):
        self.exito = exito
        self.mensaje = mensaje
        self.reserva = reserva


def validar_qr(qr_uuid, registrado_por=None):
    """
    Valida un código QR y registra asistencia si es válido.

    Reglas de negocio:
    - El QR se habilita 30 min antes de la clase y se deshabilita al terminar
    - Una vez usado el QR, es deshabilitado

    Retorna ResultadoValidacionQR con exito, mensaje y reserva.
    """
    try:
        with transaction.atomic():
            reserva = Reserva.objects.select_related('clase', 'usuario').select_for_update().get(qr_uuid=qr_uuid)

            clase = reserva.clase
            ahora = timezone.localtime(timezone.now())
            fecha_actual = ahora.date()
            hora_actual = ahora.time()

            # QR ya usado
            if reserva.qr_usado:
                return ResultadoValidacionQR(False, "Error: QR deshabilitado (ya fue usado).")

            # Reserva cancelada
            if reserva.estado == 'cancelada':
                return ResultadoValidacionQR(False, "Error: la reserva está cancelada.")

            # QR vencido (fecha de clase pasada)
            if clase.fecha < fecha_actual:
                return ResultadoValidacionQR(False, "Error: QR vencido (la clase ya pasó).")

            # QR no habilitado (fecha futura)
            if clase.fecha > fecha_actual:
                return ResultadoValidacionQR(
                    False,
                    "Error: QR no habilitado (la clase no es hoy)."
                )

            # La clase es hoy - verificar ventana de tiempo
            hora_inicio_clase = datetime.combine(fecha_actual, clase.hora_inicio)
            hora_fin_clase = datetime.combine(fecha_actual, clase.hora_fin)
            ahora_dt = datetime.combine(fecha_actual, hora_actual)

            ventana_inicio = hora_inicio_clase - timedelta(minutes=30)

            if ahora_dt < ventana_inicio:
                minutos_faltantes = int((ventana_inicio - ahora_dt).total_seconds() / 60)
                return ResultadoValidacionQR(
                    False,
                    f"Error: QR no habilitado (faltan {minutos_faltantes} minutos para la ventana de registro)."
                )

            if ahora_dt > hora_fin_clase:
                return ResultadoValidacionQR(
                    False,
                    "Error: QR vencido (la clase ya terminó)."
                )

            # Registro exitoso
            reserva.qr_usado = True
            reserva.estado = 'asistida'
            reserva.save()

            Asistencia.objects.create(
                reserva=reserva,
                presente=True,
                registrado_por=registrado_por
            )

            return ResultadoValidacionQR(
                True,
                f"Registro exitoso. Bienvenido/a {reserva.usuario.first_name or reserva.usuario.username}.",
                reserva
            )

    except Reserva.DoesNotExist:
        return ResultadoValidacionQR(False, "QR inválido: no existe reserva asociada.")
