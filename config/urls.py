from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from user import views as user_views
from django.shortcuts import render

urlpatterns = [

    path('admin/', admin.site.urls),

    path('', include('core.urls')),
    path("auth/", include("user.urls")),
    path('turno/', include('turno.urls')),
    path('pago/', include('pago.urls')),
    path('actividad/', include('actividad.urls')),
    path('resena/', include('resena.urls')),

path('reset/<uidb64>/<token>/', user_views.confirmar_restablecimiento_view, name='password_reset_confirm'),
    path('reset/done/', render, {'template_name': 'password_reset_complete.html'}, name='password_reset_complete'),
]


def handler404_view(request, exception):
    return render(request, '404.html', status=404)


def handler500_view(request):
    return render(request, '500.html', status=500)


handler404 = handler404_view
handler500 = handler500_view


