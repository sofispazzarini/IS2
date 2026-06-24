from django.urls import path
from . import views

urlpatterns = [
    path('paquete/comprar/', views.comprar_paquete, name='comprar_paquete'),
    path('paquete/confirmar/', views.confirmar_pago_paquete, name='confirmar_pago_paquete'),
    path('paquete/exito/', views.paquete_exito, name='paquete_exito'),
    path('paquete/fallo/', views.paquete_fallo, name='paquete_fallo'),
    path('paquete/pendiente/', views.paquete_pendiente, name='paquete_pendiente'),
    path('<int:reserva_id>/creditos/', views.pagar_con_creditos, name='pagar_creditos'),
    path('mercadopago/<int:reserva_id>/', views.pagar_con_mercadopago, name='pagar_con_mercadopago'),
    path('webhook/', views.webhook_mercadopago, name='webhook_mercadopago'),
    path('exito/', views.pago_exito, name='pago_exito'),
    path('fallo/', views.pago_fallo, name='pago_fallo'),
    path('pendiente/', views.pago_pendiente, name='pago_pendiente'),
    path('<int:reserva_id>/acumular-creditos/', views.acumular_creditos, name='acumular_creditos'),
    path('<int:reserva_id>/solicitar-reembolso/', views.solicitar_reembolso, name='solicitar_reembolso'),
]