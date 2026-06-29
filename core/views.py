from django.shortcuts import render
from resena.models import Resena
from resena.forms import ResenaForm
from .models import ConfiguracionSistema


def home(request):
    """Vista principal con reseñas y formulario para crear reseña."""
    
    # Traer solo reseñas generales del centro ordenadas por fecha descendente
    resenas = Resena.objects.filter(clase__isnull=True).order_by('-fecha')
    
    # Si está logueado, pasar el formulario
    form = None
    if request.user.is_authenticated:
        form = ResenaForm()
    
    context = {
        'resenas': resenas,
        'form': form,
    }
    
    return render(
        request,
        'core/home.html',
        context
    )


def mantenimiento(request):
    """Página de mantenimiento del sistema."""
    configuracion = ConfiguracionSistema.obtener()
    return render(request, 'core/mantenimiento.html', {
        'modo_mantenimiento': configuracion.modo_mantenimiento,
    })