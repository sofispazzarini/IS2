from django.urls import path
from . import views

app_name = "user"

urlpatterns = [
    path("registro/", views.registro, name="registro"),
    path('login/', views.login_view, name='login'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('change-password/', views.change_password, name='change_password'),
    path('clientes/', views.client_list, name='client_list'),
    path('clientes/buscar/', views.buscar_cliente, name='buscar_cliente'),
    path('cliente/<int:user_id>/', views.client_profile, name='client_profile'),
    path('cliente/<int:user_id>/reset-password/', views.secretary_reset_password, name='secretary_reset_password'),
    path('cliente/<int:user_id>/dar-baja/', views.dar_baja_cliente, name='dar_baja_cliente'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.registro, name='register'),

    # Profesores
    path('profesores/', views.admin_profesores, name='admin_profesores'),
    path('profesores/crear/', views.crear_profesor, name='crear_profesor'),
    path('profesores/<int:profesor_id>/modificar/', views.modificar_profesor, name='modificar_profesor'),
    path('profesores/<int:profesor_id>/eliminar/', views.eliminar_profesor, name='eliminar_profesor'),
]

