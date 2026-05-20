from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Actividad
from .forms import ActividadForm


def es_admin(user):
    return user.rol in ('secretario', 'dueno')


def es_dueno(user):
    return user.rol == 'dueno'


@login_required
def admin_actividades(request):
    """Panel de administración de actividades."""
    if not es_admin(request.user):
        messages.error(request, "No tienes permisos para acceder a esta sección.")
        return redirect('core:home')

    actividades = Actividad.objects.all().order_by('nombre')

    return render(request, 'actividad/admin_actividades.html', {
        'actividades': actividades,
        'es_dueno': es_dueno(request.user),
    })


@login_required
def crear_actividad(request):
    """Crear una nueva actividad."""
    if not es_admin(request.user):
        messages.error(request, "No tienes permisos para crear actividades.")
        return redirect('core:home')

    if request.method == 'POST':
        form = ActividadForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Actividad creada con éxito.")
            return redirect('actividad:admin_actividades')
    else:
        form = ActividadForm()

    return render(request, 'actividad/crear_actividad.html', {'form': form})


@login_required
def modificar_actividad(request, actividad_id):
    """Modificar una actividad existente."""
    if not es_dueno(request.user):
        messages.error(request, "Solo el dueño puede modificar actividades.")
        return redirect('actividad:admin_actividades')

    actividad = get_object_or_404(Actividad, id=actividad_id)

    if request.method == 'POST':
        form = ActividadForm(request.POST, instance=actividad)
        if form.is_valid():
            form.save()
            messages.success(request, "Actividad modificada con éxito.")
            return redirect('actividad:admin_actividades')
    else:
        form = ActividadForm(instance=actividad)

    return render(request, 'actividad/modificar_actividad.html', {
        'form': form,
        'actividad': actividad,
    })


@login_required
def eliminar_actividad(request, actividad_id):
    """Eliminar una actividad (solo si no tiene clases asociadas)."""
    if not es_dueno(request.user):
        messages.error(request, "Solo el dueño puede eliminar actividades.")
        return redirect('actividad:admin_actividades')

    actividad = get_object_or_404(Actividad, id=actividad_id)

    if request.method == 'POST':
        if actividad.clases.exists():
            messages.error(request, "No se puede eliminar la actividad porque tiene clases asociadas.")
            return redirect('actividad:admin_actividades')

        actividad.delete()
        messages.success(request, "Actividad eliminada con éxito.")
        return redirect('actividad:admin_actividades')

    return render(request, 'actividad/confirmar_eliminar_actividad.html', {
        'actividad': actividad,
        'tiene_clases': actividad.clases.exists(),
    })
