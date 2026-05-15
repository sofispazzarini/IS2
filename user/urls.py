from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "user"

urlpatterns = [
    path("registro/", views.registro, name="registro"),
    path('login/', views.login_view, name='login'),
    path('change-password/', views.change_password, name='change_password'),
    path('clientes/', views.client_list, name='client_list'),
    path('cliente/<int:user_id>/', views.client_profile, name='client_profile'),
    path('cliente/<int:user_id>/reset-password/', views.secretary_reset_password, name='secretary_reset_password'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.registro, name='register'),

    # URL de la HU: Pantalla donde ingresa el mail
    path('recuperar-contrasena/', views.recuperar_contrasena_view, name='recuperar_contrasena'),
]

