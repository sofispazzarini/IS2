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
        
        # Crear la reseña
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
@require_http_methods(["POST"])
def editar_resena(request, resena_id):
    """
    Editar una reseña.
    Solo el autor de la reseña puede editarla.
    """
    resena = get_object_or_404(Resena, id=resena_id)
    
    # Verificar que el usuario sea el autor de la reseña
    if resena.usuario != request.user:
        messages.error(request, 'No tienes permiso para editar esta reseña.')
        return redirect('core:home')
    
    form = ResenaForm(request.POST, instance=resena)
    
    if form.is_valid():
        form.save()
        messages.success(request, 'Reseña modificada correctamente.')
    else:
        # Pasar errores al template
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, error)
    
    return redirect('core:home')


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
    return redirect('core:home')
