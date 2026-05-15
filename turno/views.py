from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Clase, Reserva, ListaEspera, Asistencia
from .forms import ClaseForm


def reservas_view(request):
    clases = Clase.objects.filter(cancelada=False)
    return render(request, 'turno/reservas.html', {'clases': clases})

def crear_clase_view(request):
    if request.method == 'POST':
        form = ClaseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'clase creada con éxito')
            return redirect('crear_clase')
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = ClaseForm()
    
    return render(request, 'turno/crear_clase.html', {'form': form})

def lista_clases_admin(request):
    clases = Clase.objects.all().order_by('fecha', 'hora_inicio')
    return render(request, 'turno/lista_clases_admin.html', {'clases': clases})

def editar_clase_view(request, pk):
    clase = get_object_or_404(Clase, pk=pk)
    if request.method == 'POST':
        form = ClaseForm(request.POST, instance=clase)
        if form.is_valid():
            form.save()
            messages.success(request, 'Clase actualizada con éxito')
            return redirect('lista_clases_admin')
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = ClaseForm(instance=clase)
    
    return render(request, 'turno/crear_clase.html', {'form': form, 'editando': True})

def cancelar_clase_view(request, pk):
    clase = get_object_or_404(Clase, pk=pk)
    if request.method == 'POST':
        nombre_actividad = clase.actividad.nombre
        clase.delete() 
        messages.success(request, f'La clase de {nombre_actividad} ha sido eliminada definitivamente.')
        return redirect('lista_clases_admin')
    
    return render(request, 'turno/confirmar_cancelacion.html', {'clase': clase})

def ver_inscriptos_view(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id)
    
    reservas = Reserva.objects.filter(clase=clase).exclude(estado='cancelada')
    
    return render(request, 'turno/ver_inscriptos.html', {
        'clase': clase,
        'reservas': reservas
    })

def registrar_asistencia_view(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    clase_id = reserva.clase.id
    
    if request.method == 'POST':
    
        if reserva.estado != 'confirmada':
            messages.error(request, "El cliente debe abonar para registrar su asistencia.")
        else:
            Asistencia.objects.get_or_create(
                reserva=reserva,
                defaults={
                    'presente': True,
                    'registrado_por': request.user if request.user.is_authenticated else None
                }
            )
            reserva.estado = 'asistida'
            reserva.save()
            
            messages.success(request, f"Asistencia registrada con éxito para {reserva.usuario.username}.")
            
    return redirect('/turno/administracion/clases/' + str(clase_id) + '/inscriptos/')

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
        return redirect('reserva_exitosa', reserva_id=nueva_reserva.id)

    return render(request, 'turno/pedir_turno.html', {'clase': clase})

@login_required
def reserva_exitosa(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)
    return render(request, 'turno/reserva_exitosa.html', {'reserva': reserva})

@login_required
def cancelar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)
    clase = reserva.clase
    hoy = timezone.now().date()

    if (clase.fecha - hoy) < timedelta(days=2):
        messages.error(request, "Las cancelaciones con menos de dos días de anticipación no están permitidas.")
        return redirect('reservas')

    if request.method == 'POST':
        reserva.estado = 'cancelada'
        reserva.save()
        
        if reserva.estado == 'pendiente_pago':
            messages.success(request, "La cancelación fue exitosa. Se aumentó la disponibilidad de cupos.")
        else:
            messages.success(request, "La cancelación fue exitosa. ¿Deseas la devolución del dinero o acumulación de créditos?")
            
        return redirect('reservas')

    return render(request, 'turno/confirmar_cancelacion.html', {'reserva': reserva})