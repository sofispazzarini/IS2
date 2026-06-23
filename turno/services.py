import uuid
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction

from .models import Reserva, Asistencia

from django.core.exceptions import ValidationError


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
        uuid.UUID(str(qr_uuid))
    except (ValueError, AttributeError):
        return ResultadoValidacionQR(False, "QR inválido: el código no tiene un formato válido.")

    try:
        with transaction.atomic():
            reserva = Reserva.objects.select_related('clase', 'usuario').select_for_update().get(qr_uuid=qr_uuid)

            clase = reserva.clase
            ahora = timezone.localtime(timezone.now())
            fecha_actual = ahora.date()
            hora_actual = ahora.time()

            # QR ya usado
            if reserva.qr_usado:
                return ResultadoValidacionQR(False, "QR ya usado")

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

def registrar_asistencia_manual(reserva_id):
    reserva = Reserva.objects.get(id=reserva_id)
    
    # REGLA DE NEGOCIO: El turno debe estar registrado como “Abonado” (Confirmada)
    if reserva.estado != 'confirmada':
        raise ValidationError("El cliente debe abonar para registrar su asistencia.")
    
    # Escenario I: Registro exitoso
    reserva.estado = 'asistida'
    reserva.qr_usado = True  # Ya ingresó, el QR se da por usado
    reserva.save()
    
    return reserva