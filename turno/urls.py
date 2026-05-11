from django.urls import path
from . import views

urlpatterns = [
    path('reservas/', views.reservas_view, name='reservas'),
]

#reemplazar? 
from django.urls import path
from . import views

urlpatterns = [
    path('clases/', views.lista_clases, name='lista_clases'),
    path('clases/<int:clase_id>/reservar/', views.pedir_turno, name='pedir_turno'),
    path('clases/<int:clase_id>/reserva-exitosa/', views.reserva_exitosa, name='reserva_exitosa'),
]