from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Clase
from .forms import ClaseForm

# VISTA DEL CLIENTE RESERVAR CLASE
def reservas_view(request):
    clases = Clase.objects.filter(cancelada=False)
    return render(request, 'turno/reservas.html', {'clases': clases})

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