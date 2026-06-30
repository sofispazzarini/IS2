from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods

from .models import Resena
from .forms import ResenaForm
from actividad.models import Actividad


@login_required(login_url='user:login')
@require_http_methods(["POST"])
def crear_resena(request):
    """
    Crear una nueva reseña.
    Solo usuarios logueados pueden acceder.
    """
    form = ResenaForm(request.POST)
    
    if form.is_valid():
        # Obtener o crear actividad por defecto (para cumplir con el modelo)
        actividad, _ = Actividad.objects.get_or_create(
            nombre='Centro',
            defaults={
                'descripcion': 'Reseña general del centro',
                'duracion_min': 0,
                'precio': 0.00,
                'activa': True,
            }
        )
        
        # CHEQUEO DE LA REGLA DE NEGOCIO: ¿Ya existe una reseña de este usuario para esta actividad?
        ya_existe = Resena.objects.filter(usuario=request.user, actividad=actividad).exists()
        
        if ya_existe:
            messages.error(
                request, 
                'Ya has enviado una reseña anteriormente. No puedes dejar más de una.'
            )
            return redirect('core:home')
        
        # Si no existe, procedemos a crearla normalmente
        resena = form.save(commit=False)
        resena.usuario = request.user
        resena.actividad = actividad
        resena.puntuacion = 5  # Puntuación por defecto
        resena.save()
        
        messages.success(
            request,
            'Tu reseña fue enviada exitosamente.'
        )
    else:
        # Pasar errores al template
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, error)
    
    return redirect('core:home')


@login_required(login_url='user:login')
@require_http_methods(["GET", "POST"])
def editar_resena(request, resena_id):
    """
    Editar una reseña de clase.
    Solo el autor de la reseña puede editarla.
    """
    resena = get_object_or_404(Resena, id=resena_id)

    if resena.usuario != request.user:
        messages.error(request, 'No tienes permiso para editar esta reseña.')
        return redirect('core:home')

    if request.method == 'POST':
        form = ResenaForm(request.POST, instance=resena)
        if form.is_valid():
            form.save()
            messages.success(request, 'Reseña modificada correctamente.')
            return redirect('user:mi_historial')
        else:
            messages.error(request, 'No se pudo modificar la reseña.')
    else:
        form = ResenaForm(instance=resena)

    return render(request, 'resena/editar_resena_clase.html', {
        'form': form,
        'resena': resena,
    })


@login_required(login_url='user:login')
@require_http_methods(["POST"])
def eliminar_resena(request, resena_id):
    """
    Eliminar una reseña.
    Solo el autor de la reseña puede eliminarla.
    """
    resena = get_object_or_404(Resena, id=resena_id)
    
    if resena.usuario != request.user:
        messages.error(request, 'No tienes permiso para eliminar esta reseña.')
        return redirect('core:home')
    
    resena.delete()
    messages.success(request, 'Reseña eliminada exitosamente.')
    return redirect('user:mi_historial')

@login_required(login_url='user:login')
def crear_resena_clase(request, clase_id):
    """
    Crear reseña de una clase específica.
    Condiciones: usuario asistió a la clase Y tiene pago aprobado.
    """
    from turno.models import Clase, Reserva
    from pago.models import Pago

    clase = get_object_or_404(Clase, id=clase_id)

    # Condición 1: el usuario tiene una reserva con estado 'asistida' para esta clase
    reserva = Reserva.objects.filter(
        usuario=request.user,
        clase=clase,
        estado='asistida'
    ).first()

    if not reserva:
        messages.error(request, 'Solo podés reseñar una clase a la que hayas asistido.')
        return redirect('core:home')

    # Condición 2: esa reserva tiene un pago aprobado
    pago_aprobado = Pago.objects.filter(
        reserva=reserva,
        estado_pago='aprobado'
    ).exists()

    if not pago_aprobado:
        messages.error(request, 'Solo podés reseñar una clase que hayas pagado.')
        return redirect('core:home')

    # Condición 3: no existe ya una reseña de este usuario para esta clase
    ya_existe = Resena.objects.filter(usuario=request.user, clase=clase).exists()
    if ya_existe:
        messages.error(request, 'Ya enviaste una reseña para esta clase.')
        return redirect('core:home')

    if request.method == "POST":

        form = ResenaForm(request.POST)

        if form.is_valid():
            resena = form.save(commit=False)
            resena.usuario = request.user
            resena.clase = clase
            resena.actividad = clase.actividad
            resena.puntuacion = 5
            resena.save()

            messages.success(request, 'Tu reseña fue enviada exitosamente.')
            return redirect("user:mi_historial")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = ResenaForm()

    return render(
        request,
        "resena/crear_resena_clase.html",
        {
            "form": form,
            "clase": clase,
        },
    )