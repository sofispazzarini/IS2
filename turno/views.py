from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Clase
from .forms import ClaseForm

# VISTA DEL CLIENTE RESERVAR CLASE
def reservas_view(request):
    clases = Clase.objects.filter(cancelada=False)
    return render(request, 'reservas.html', {'clases': clases})

# HU CREAR CLASE SECRETARIO / DUENO
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
    
    return render(request, 'crear_clase.html', {'form': form})

# NUEVA: LISTA DE GESTIÓN PARA EL DUEÑO/SECRETARIO
def lista_clases_admin(request):
    # Traemos todas para que el admin pueda ver qué canceló y qué no
    clases = Clase.objects.all().order_by('fecha', 'hora_inicio')
    return render(request, 'lista_clases_admin.html', {'clases': clases})

# NUEVA: MODIFICAR CLASE EXISTENTE
def editar_clase_view(request, pk):
    clase = get_object_or_404(Clase, pk=pk)
    if request.method == 'POST':
        # Al pasar instance=clase, Django sabe que debe actualizar y no crear uno nuevo
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
    
    # Reutilizamos el template de crear, pasando una variable 'editando' para cambiar el título
    return render(request, 'crear_clase.html', {'form': form, 'editando': True})

# NUEVA: CANCELAR CLASE (Baja Lógica)
def cancelar_clase_view(request, pk):
    clase = get_object_or_404(Clase, pk=pk)
    
    if request.method == 'POST':
        nombre_actividad = clase.actividad.nombre # Guardamos el nombre para el mensaje
        clase.delete() # <--- Aquí es donde se borra físicamente de la DB
        messages.success(request, f'La clase de {nombre_actividad} ha sido eliminada definitivamente.')
        return redirect('lista_clases_admin')
    
    return render(request, 'confirmar_cancelacion.html', {'clase': clase})