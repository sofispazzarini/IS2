from datetime import timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from .models import Clase, Reserva, ListaEspera


@login_required
def mis_turnos(request):
    """Muestra los turnos/reservas próximas del usuario."""
    hoy = timezone.now().date()

    reservas = Reserva.objects.filter(
        usuario=request.user,
        clase__fecha__gte=hoy
    ).exclude(
        estado='cancelada'
    ).select_related('clase', 'clase__actividad', 'clase__profesor').order_by('clase__fecha', 'clase__hora_inicio')

    reservas_con_info = []
    for reserva in reservas:
        dias_anticipacion = (reserva.clase.fecha - hoy).days
        puede_cancelar = dias_anticipacion >= 2
        reservas_con_info.append({
            'reserva': reserva,
            'puede_cancelar': puede_cancelar,
            'dias_anticipacion': dias_anticipacion,
        })

    return render(request, 'turno/mis_turnos.html', {
        'reservas_con_info': reservas_con_info,
        'tiene_turnos': len(reservas_con_info) > 0,
    })

@login_required
def lista_clases(request):
    """Muestra todas las clases disponibles que no han sido canceladas."""
    clases = Clase.objects.filter(
        cancelada=False,
        fecha__gte=timezone.now().date()
    ).order_by('fecha', 'hora_inicio')
    return render(request, 'turno/lista_clases.html', {'clases': clases})

@login_required
def pedir_turno(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id)
    usuario = request.user

    if request.method == 'POST':
        # 1. Escenario III: Superposición de turnos
        superposicion = Reserva.objects.filter(
            usuario=usuario,
            clase__fecha=clase.fecha,
            clase__hora_inicio=clase.hora_inicio,
        ).exclude(estado='cancelada').exists()

        if superposicion:
            # En lugar de explotar, mandamos el error al mismo template
            return render(request, 'turno/pedir_turno.html', {
                'clase': clase,
                'error': 'Error por superposición de turnos.'
            })

        # 2. Verificar cupo
        reservas_activas = Reserva.objects.filter(
            clase=clase
        ).exclude(estado='cancelada').count()

        if reservas_activas >= clase.cupo_maximo:
            # Escenario II: Lista de espera
            ListaEspera.objects.get_or_create(usuario=usuario, clase=clase)
            messages.info(request, "No hay cupos disponibles. Has sido agregado a la lista de espera.")
            return redirect('lista_clases')

        # 3. Escenario I: Reserva exitosa
        nueva_reserva = Reserva.objects.create(
            usuario=usuario,
            clase=clase,
            estado='pendiente_pago'
        )
        # IMPORTANTE: Pasamos el ID de la reserva a la página de éxito
        return redirect('reserva_exitosa', reserva_id=nueva_reserva.id)

    return render(request, 'turno/pedir_turno.html', {'clase': clase})
@login_required
def reserva_exitosa(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)
    return render(request, 'turno/reserva_exitosa.html', {'reserva': reserva})


@login_required
def cancelar_reserva(request, reserva_id):
    # Buscamos la reserva del usuario actual
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)
    clase = reserva.clase
    hoy = timezone.now().date()

    # REGLA DE NEGOCIO: Mínimo 2 días de anticipación
    # Si la clase es el 16 y hoy es 14, la diferencia es 2 (Permitido)
    # Si la clase es el 15 y hoy es 14, la diferencia es 1 (No permitido)
    if (clase.fecha - hoy) < timedelta(days=2):
        # Escenario III: Cancelación fallida
        messages.error(request, "Las cancelaciones con menos de dos días de anticipación no están permitidas.")
        return redirect('reservas')

    if request.method == 'POST':
        estado_anterior = reserva.estado
        reserva.estado = 'cancelada'
        reserva.save()

        if estado_anterior == 'pendiente_pago':
            messages.success(request, "La cancelación fue exitosa. Se aumentó la disponibilidad de cupos.")
        else:
            messages.success(request, "La cancelación fue exitosa. ¿Deseas la devolución del dinero o acumulación de créditos?")

        return redirect('reservas')

    return render(request, 'turno/confirmar_cancelacion.html', {'reserva': reserva})
