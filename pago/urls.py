from django.urls import path
from . import views

urlpatterns = [
    path('<int:reserva_id>/creditos/', views.pagar_con_creditos, name='pagar_creditos'),
    path('mercadopago/<int:reserva_id>/', views.pagar_con_mercadopago, name='pagar_con_mercadopago'),
    path('webhook/', views.webhook_mercadopago, name='webhook_mercadopago'),
    path('exito/', views.pago_exito, name='pago_exito'),
    path('fallo/', views.pago_fallo, name='pago_fallo'),
    path('pendiente/', views.pago_pendiente, name='pago_pendiente'),
]