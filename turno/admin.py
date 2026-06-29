from django.contrib import admin
from .models import Clase, Profesor, Actividad, TurnoFijo, Abono


@admin.register(Clase)
class ClaseAdmin(admin.ModelAdmin):
    list_display = ('actividad', 'fecha', 'hora_inicio', 'profesor', 'cupo_maximo')
    list_filter = ('actividad', 'fecha', 'profesor')
    search_fields = ('actividad__nombre', 'profesor__nombre')


@admin.register(Profesor)
class ProfesorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido', 'email', 'telefono', 'especialidad')
    search_fields = ('nombre', 'apellido', 'email')


@admin.register(Actividad)
class ActividadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio', 'duracion_min', 'activa')
    list_filter = ('activa',)


@admin.register(TurnoFijo)
class TurnoFijoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'actividad', 'dia_semana', 'hora_inicio', 'activo')
    list_filter = ('activo', 'dia_semana', 'actividad')
    search_fields = ('usuario__email', 'usuario__first_name', 'usuario__last_name')
    raw_id_fields = ('usuario',)


@admin.register(Abono)
class AbonoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'mes', 'anio', 'estado_pago', 'monto_final', 'descuento_porcentaje')
    list_filter = ('estado_pago', 'anio', 'mes')
    search_fields = ('usuario__email', 'usuario__first_name', 'usuario__last_name')
    raw_id_fields = ('usuario',)