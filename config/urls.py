from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from user import views as user_views

urlpatterns = [

    path('admin/', admin.site.urls),

    path('', include('core.urls')),
    path("auth/", include("user.urls")),
    path('turno/', include('turno.urls')),
    path('resena/', include('resena.urls')),

    path('reset/<uidb64>/<token>/', user_views.cambiar_contrasena_view, name='password_reset_confirm'),
    
    path('reset/done/', user_views.render, {'template_name': 'password_reset_complete.html'}, name='password_reset_complete'),
]


