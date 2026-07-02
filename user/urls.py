from django.urls import path
from . import views

app_name = "user"

urlpatterns = [
    path("registro/", views.registro, name="registro"),
    path('login/', views.login_view, name='login'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('change-password/', views.change_password, name='change_password'),
    path('recuperar-contrasena/', views.recuperar_contrasena_view, name='recuperar_contrasena'),
    path('clientes/', views.client_list, name='client_list'),
    path('clientes/buscar/', views.buscar_cliente, name='buscar_cliente'),
    path('cliente/<int:user_id>/', views.client_profile, name='client_profile'),
    path('cliente/<int:user_id>/historial-pagos/', views.historial_pagos_cliente, name='historial_pagos_cliente'),
    path('cliente/<int:user_id>/historial-asistencias/', views.historial_asistencias, name='historial_asistencias'),
    path('cliente/<int:user_id>/editar/', views.editar_cliente, name='editar_cliente'),
    path('cliente/<int:user_id>/reset-password/', views.secretary_reset_password, name='secretary_reset_password'),
    path('cliente/<int:user_id>/dar-baja/', views.dar_baja_cliente, name='dar_baja_cliente'),
    path('mi-historial/', views.mi_historial, name='mi_historial'),
    path('logout/', views.logout_view, name='logout'),
    path('mantenimiento/toggle/', views.toggle_modo_mantenimiento, name='toggle_modo_mantenimiento'),
    path('register/', views.registro, name='register'),

    path('estadisticas/', views.estadisticas_usuario, name='estadisticas_usuario'),
    
    # Profesores
    path('profesores/', views.admin_profesores, name='admin_profesores'),
    path('profesores/crear/', views.crear_profesor, name='crear_profesor'),
    path('profesores/<int:profesor_id>/modificar/', views.modificar_profesor, name='modificar_profesor'),
    path('profesores/<int:profesor_id>/eliminar/', views.eliminar_profesor, name='eliminar_profesor'),
    path('profesores/<int:profesor_id>/toggle/', views.toggle_profesor, name='toggle_profesor'),
   
    # Secretarios
    path('secretarios/', views.admin_secretarios, name='admin_secretarios'),
    path('secretarios/crear/', views.crear_secretario, name='crear_secretario'),
    path('secretarios/<int:secretario_id>/modificar/', views.modificar_secretario, name='modificar_secretario'),
    path('secretarios/<int:secretario_id>/eliminar/', views.eliminar_secretario, name='eliminar_secretario'),
]

