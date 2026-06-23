import uuid

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

from datetime import datetime

from user.models import User, Profesor
from actividad.models import Actividad

class Salon(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

class Clase(models.Model):

    actividad = models.ForeignKey(
        'actividad.Actividad', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='clases'
    )
    profesor = models.ForeignKey(
        'user.Profesor', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='clases'
    )

    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    cupo_maximo = models.IntegerField()
    
    salon = models.ForeignKey(
        Salon, 
        on_delete=models.PROTECT, 
        related_name='clases'
    )
    cancelada = models.BooleanField(default=False)
    motivo_cancelacion = models.TextField(
        blank=True,
        null=True
    )

    @property
    def ya_paso(self):
        """Devuelve True si la clase ya comenzó (comparando con la hora local actual)"""
        if not self.fecha or not self.hora_inicio:
            return False
        
        # Combinamos la fecha y hora de la clase
        fecha_hora_clase = datetime.combine(self.fecha, self.hora_inicio)
        
        # Obtenemos la hora local actual del servidor (asumiendo tu TIME_ZONE de Argentina)
        ahora_local = timezone.localtime(timezone.now())
        
        # Hacemos que la fecha de la clase tenga la misma zona horaria local para comparar manzanas con manzanas
        fecha_hora_clase = timezone.make_aware(fecha_hora_clase, ahora_local.tzinfo)
            
        # Si la hora actual es mayor o igual a la hora de inicio, ya no se puede tocar
        return ahora_local >= fecha_hora_clase

    def clean(self):
        # Validación original al crear la clase
        if self._state.adding: 
            if self.fecha and self.fecha < timezone.localdate():
                raise ValidationError('No puedes crear una actividad para una fecha pasada')
        
        # NUEVA VALIDACIÓN: Si el objeto ya existe (se está modificando o cancelando) y ya pasó, bloquea la acción
        else:
            if self.ya_paso:
                raise ValidationError('No puedes modificar ni cancelar una clase que ya ha finalizado.')

        # 2. ACTUALIZADO AQUÍ: Django ahora comparará usando la instancia o el ID del salón de manera automática
        salon_ocupado = Clase.objects.filter(
            fecha=self.fecha,
            hora_inicio=self.hora_inicio,
            salon=self.salon
        ).exclude(pk=self.pk)

        if salon_ocupado.exists():
            raise ValidationError('El salón seleccionado ya está ocupado en esa fecha y horario.')

        profesor_ocupado = Clase.objects.filter(
            fecha=self.fecha,
            hora_inicio=self.hora_inicio,
            profesor=self.profesor
        ).exclude(pk=self.pk)

        if profesor_ocupado.exists():
            raise ValidationError('El profesor seleccionado ya tiene otra clase asignada en esa fecha y horario.')
        
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.actividad.nombre} - {self.fecha}"


class Reserva(models.Model):

    ESTADOS = (
        ('pendiente_pago', 'Pendiente de pago'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
        ('asistida', 'Asistida'),
        ('ausente', 'Ausente'),
    )

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reservas'
    )

    clase = models.ForeignKey(
        Clase,
        on_delete=models.CASCADE,
        related_name='reservas'
    )

    fecha_reserva = models.DateTimeField(auto_now_add=True)

    estado = models.CharField(
        max_length=30,
        choices=ESTADOS,
        default='pendiente_pago'
    )

    qr_uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )

    qr_usado = models.BooleanField(default=False)

    observaciones = models.TextField(
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.usuario.username} - {self.clase}"


class Asistencia(models.Model):

    reserva = models.OneToOneField(
        Reserva,
        on_delete=models.CASCADE,
        related_name='asistencia'
    )

    fecha_registro = models.DateTimeField(auto_now_add=True)

    presente = models.BooleanField(default=True)

    registrado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )

    def __str__(self):
        return f"Asistencia - {self.reserva}"


class ListaEspera(models.Model):

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    clase = models.ForeignKey(
        Clase,
        on_delete=models.CASCADE
    )

    fecha_ingreso = models.DateTimeField(auto_now_add=True)

    notificado = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.usuario.username} - {self.clase}"