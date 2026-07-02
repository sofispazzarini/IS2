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

    estado = request.GET.get('estado', '')
    busqueda = request.GET.get('q', '').strip()

    actividades = Actividad.objects.all()

    if estado == 'activas':
        actividades = actividades.filter(activa=True)
    elif estado == 'inactivas':
        actividades = actividades.filter(activa=False)
    if busqueda:
        actividades = actividades.filter(nombre__icontains=busqueda)

    actividades = actividades.order_by('nombre')

    return render(request, 'actividad/admin_actividades.html', {
        'actividades': actividades,
        'es_dueno': es_dueno(request.user),
        'filtro_estado': estado,
        'filtro_busqueda': busqueda,
        'hay_filtros': any([estado, busqueda]),
    })


@login_required
def crear_actividad(request):
    """Crear una nueva actividad (solo dueño)."""
    if not es_dueno(request.user):
        messages.error(request, "Solo el dueño puede crear actividades.")
        return redirect('actividad:admin_actividades')

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
            # 🟢 VALIDACIÓN: Si el formulario es válido pero no sufrió modificaciones
            if not form.has_changed():
                messages.info(request, "No se registraron cambios en la actividad.")
                return redirect('actividad:admin_actividades')
                
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
    """Eliminar una actividad (solo si no tiene clases activas)."""
    if not es_dueno(request.user):
        messages.error(request, "Solo el dueño puede modificar actividades.")
        return redirect('actividad:admin_actividades')

    actividad = get_object_or_404(Actividad, id=actividad_id)

    # 🔍 Filtramos para ver si tiene clases que NO estén canceladas
    tiene_clases_activas = actividad.clases.filter(cancelada=False).exists()

    if request.method == 'POST':
        if not actividad.activa:
            messages.info(request, "La actividad ya está inactiva.")

            return redirect('actividad:admin_actividades')
        actividad.activa = False
        actividad.save()
        return redirect('actividad:admin_actividades')

    return render(request, 'actividad/confirmar_eliminar_actividad.html', {
        'actividad': actividad,
        'tiene_clases': tiene_clases_activas,  # Mandamos el filtro corregido al template
    })

@login_required
def toggle_actividad(request, actividad_id):
    """Habilitar o deshabilitar una actividad."""
    if not es_dueno(request.user):
        messages.error(request, "Solo el dueño puede modificar actividades.")
        return redirect('actividad:admin_actividades')

    actividad = get_object_or_404(Actividad, id=actividad_id)

    if request.method == 'POST':
        actividad.activa = not actividad.activa
        actividad.save()
        estado = "habilitada" if actividad.activa else "Inhabilitada"
        messages.success(request, f"Actividad {estado} ")

    return redirect('actividad:admin_actividades')