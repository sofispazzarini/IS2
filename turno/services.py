import uuid
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction

from .models import Reserva, Asistencia, Clase, ClaseFija

from django.core.exceptions import ValidationError


class ResultadoValidacionQR:
    def __init__(self, exito, mensaje, reserva=None):
        self.exito = exito
        self.mensaje = mensaje
        self.reserva = reserva


def validar_qr(qr_uuid, registrado_por=None):
    """
    Valida un codigo QR y registra asistencia si es valido.

    Reglas de negocio:
    - El QR se habilita 30 min antes de la clase y se deshabilita al terminar
    - Una vez usado el QR, es deshabilitado

    Retorna ResultadoValidacionQR con exito, mensaje y reserva.
    """
    try:
        uuid.UUID(str(qr_uuid))
    except (ValueError, AttributeError):
        return ResultadoValidacionQR(False, "Error: QR no reconocido.")

    try:
        with transaction.atomic():
            reserva = Reserva.objects.select_related('clase', 'usuario').select_for_update().get(qr_uuid=qr_uuid)

            clase = reserva.clase
            ahora = timezone.localtime(timezone.now())
            fecha_actual = ahora.date()
            hora_actual = ahora.time()

            # QR ya usado
            if reserva.qr_usado:
                return ResultadoValidacionQR(False, "Error: QR ya fue usado.")

            # Reserva cancelada
            if reserva.estado == 'cancelada':
                return ResultadoValidacionQR(False, "Error: la reserva esta cancelada.")

            # QR vencido (fecha de clase pasada)
            if clase.fecha < fecha_actual:
                return ResultadoValidacionQR(False, "Este QR perdió su tiempo de validez.")

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
                    "Este QR perdió su tiempo de validez."
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
        return ResultadoValidacionQR(False, "Error: QR no reconocido.")


def registrar_asistencia_manual(reserva_id):
    reserva = Reserva.objects.select_related('clase').get(id=reserva_id)

    # REGLA DE NEGOCIO: No registrar asistencia a clases que ya terminaron
    ahora_local = timezone.localtime(timezone.now())
    clase = reserva.clase
    fin_ventana = timezone.make_aware(
        datetime.combine(clase.fecha, clase.hora_inicio) + timedelta(hours=1, minutes=30),
        ahora_local.tzinfo
    )
    if ahora_local > fin_ventana:
        raise ValidationError("No se puede registrar asistencia a una clase que ya finalizo.")

    # REGLA DE NEGOCIO: El turno debe estar registrado como Abonado (Confirmada)
    if reserva.estado != 'confirmada':
        raise ValidationError("El cliente debe abonar para registrar su asistencia.")

    # Escenario I: Registro exitoso
    reserva.estado = 'asistida'
    reserva.qr_usado = True
    reserva.save()

    return reserva


HORIZONTE_DIAS = 28  # horizonte rodante: 4 semanas


def _proxima_fecha(dia_semana, desde):
    """Primera fecha >= desde que cae en dia_semana (weekday(): 0=Lunes)."""
    delta = (dia_semana - desde.weekday()) % 7
    return desde + timedelta(days=delta)


def generar_clases_fijas():
    """Garantiza que cada ClaseFija activa tenga sus Clase generadas
    para las próximas 4 semanas. Idempotente: no duplica fechas ya
    generadas (incluidas las canceladas, que no se resucitan) y saltea
    silenciosamente las ocurrencias en conflicto de salón/profesor."""
    hoy = timezone.localdate()
    limite = hoy + timedelta(days=HORIZONTE_DIAS)

    for regla in ClaseFija.objects.filter(activa=True).select_related(
            'actividad', 'profesor', 'salon'):
        if regla.actividad_id is None or regla.profesor_id is None:
            continue  # regla huérfana (actividad/profesor borrados): no generar
        inicio = max(regla.fecha_inicio, hoy)
        fecha = _proxima_fecha(regla.dia_semana, inicio)

        existentes = set(Clase.objects.filter(
            clase_fija=regla, fecha__gte=inicio, fecha__lte=limite,
        ).values_list('fecha', flat=True))

        while fecha <= limite:
            if fecha not in existentes:
                try:
                    Clase.objects.create(
                        actividad=regla.actividad, profesor=regla.profesor,
                        salon=regla.salon, fecha=fecha,
                        hora_inicio=regla.hora_inicio, hora_fin=regla.hora_fin,
                        cupo_maximo=regla.cupo_maximo, clase_fija=regla,
                    )
                except ValidationError:
                    pass  # ocurrencia puntual en conflicto: se saltea solo esa fecha
            fecha += timedelta(days=7)
