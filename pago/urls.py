from django.urls import path
from . import views

urlpatterns = [
    path('<int:reserva_id>/tarjeta/', views.pagar_con_tarjeta, name='pagar_tarjeta'),
    path('<int:reserva_id>/creditos/', views.pagar_con_creditos, name='pagar_creditos'),
]