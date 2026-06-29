from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from django.db import transaction
from turno.models import Reserva
from user.models import Penalizacion

class Command(BaseCommand):
    help = 'Revisa las clases finalizadas hace más de 30 min y pasa a ausente a quienes no asistieron.'

    def handle(self, *args, **options):
        ahora = timezone.localtime(timezone.now())
        hoy = ahora.date()
        
        # 1. Buscamos reservas activas de clases de hoy o días anteriores
        reservas_potenciales = Reserva.objects.filter(
            estado__in=['pendiente_pago', 'confirmada'],
            clase__fecha__lte=hoy
        ).select_related('clase', 'usuario')

        ausentes_detectados = 0

        for reserva in reservas_potenciales:
            clase = reserva.clase
            
            # Combinamos la fecha y hora de fin de la clase
            clase_fin_dt = datetime.combine(clase.fecha, clase.hora_fin)
            clase_fin_dt = timezone.make_aware(clase_fin_dt)
            
            # Margen de 30 minutos de gracia
            limite_tolerancia = clase_fin_dt + timedelta(minutes=30)
            
            # Si ya pasó la tolerancia y sigue en este estado, es ausente involuntario
            if ahora > limite_tolerancia:
                with transaction.atomic():
                    # Cambiamos estado
                    reserva.estado = 'ausente'
                    reserva.save()
                    ausentes_detectados += 1
                    
                    # Contamos penalizaciones activas actuales del usuario
                    penalizaciones_actuales = Penalizacion.objects.filter(
                        usuario=reserva.usuario,
                        activa=True
                    ).count()
                    
                    # 🚀 REGLA: Aplicar penalización solo si tiene menos de 2 activas (0 o 1)
                    if penalizaciones_actuales < 2:
                        Penalizacion.objects.create(
                            usuario=reserva.usuario,
                            motivo=f"Ausencia automatizada: Clase de {clase.actividad.nombre} del {clase.fecha.strftime('%d/%m/%Y')}.",
                            activa=True
                        )
                        self.stdout.write(self.style.SUCCESS(f"Penalizado: {reserva.usuario.username}"))
                    else:
                        self.stdout.write(self.style.WARNING(f"Usuario {reserva.usuario.username} ya tiene {penalizaciones_actuales} penalizaciones. No se agrega otra."))

        if ausentes_detectados > 0:
            self.stdout.write(self.style.SUCCESS(f"Proceso terminado con éxito. Se detectaron {ausentes_detectados} ausentes."))
        else:
            self.stdout.write(self.style.NOTICE("No se encontraron nuevos ausentes para procesar."))