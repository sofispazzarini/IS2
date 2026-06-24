from .models import ConfiguracionSistema


def mantenimiento_context(request):
    modo_mantenimiento_activo = False
    es_dueno = False

    if request.user.is_authenticated:
        es_dueno = getattr(request.user, 'rol', None) == 'dueno'
        if es_dueno:
            configuracion = ConfiguracionSistema.obtener()
            modo_mantenimiento_activo = configuracion.modo_mantenimiento

    return {
        'es_dueno': es_dueno,
        'modo_mantenimiento_activo': modo_mantenimiento_activo,
    }
