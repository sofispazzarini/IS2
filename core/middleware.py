from django.shortcuts import redirect

from .models import ConfiguracionSistema


class MantenimientoMiddleware:
    """Redirige a la página de mantenimiento cuando el modo está activo."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.process_request(request)
        if response:
            return response
        return self.get_response(request)

    def process_request(self, request):
        try:
            configuracion = ConfiguracionSistema.objects.get(pk=1)
        except ConfiguracionSistema.DoesNotExist:
            return None

        if not configuracion.modo_mantenimiento:
            return None

        request_path = request.path
        allowed_prefixes = [
            '/static/',
            '/auth/login/',
            '/auth/logout/',
            '/user/mantenimiento/toggle/',
            '/reset/',
            '/maintenance/',
        ]

        if any(request_path.startswith(prefix) for prefix in allowed_prefixes):
            return None

        if request.user.is_authenticated and getattr(request.user, 'rol', None) == 'dueno':
            return None

        return redirect('core:maintenance')
