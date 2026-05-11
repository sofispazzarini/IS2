from django.shortcuts import render


def reservas_view(request):
    return render(request, 'turno/reservas.html')

#reemplazar?

from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Clase, Reserva, ListaEspera

@login_required
def lista_clases(request):
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
        # Verificar superposición de turnos
        superposicion = Reserva.objects.filter(
            usuario=usuario,
            clase__fecha=clase.fecha,
            clase__hora_inicio=clase.hora_inicio,
        ).exclude(estado='cancelada').exists()

        if superposicion:
            return render(request, 'turno/pedir_turno.html', {
                'clase': clase,
                'error': 'Ya tenés una reserva para ese horario.'
            })

        # Verificar cupo
        reservas_activas = Reserva.objects.filter(
            clase=clase
        ).exclude(estado='cancelada').count()

        if reservas_activas >= clase.cupo_maximo:
            ListaEspera.objects.get_or_create(usuario=usuario, clase=clase)
            return render(request, 'turno/pedir_turno.html', {
                'clase': clase,
                'error': 'No hay cupos disponibles. Fuiste agregado a la lista de espera.'
            })

        # Crear reserva
        Reserva.objects.create(
            usuario=usuario,
            clase=clase,
            estado='pendiente_pago'
        )
        return redirect('reserva_exitosa', clase_id=clase.id)

    return render(request, 'turno/pedir_turno.html', {'clase': clase})

@login_required
def reserva_exitosa(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id)
    return render(request, 'turno/reserva_exitosa.html', {'clase': clase})