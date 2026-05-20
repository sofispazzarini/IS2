from decimal import Decimal

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from turno.models import Reserva
from .models import Pago

def simular_servidor_pago(numero, codigo, titular):
    # Simulacion del servidor de pago externo
    tarjetas_validas = {
        '111 222 333 444': {
            'codigo': '987',
            'titular': 'Juan Ignacio Torres',
            'activa': True,
            'fondos': 50000,
            'vencida': False,
        }
    }
    if numero not in tarjetas_validas:
        return 'numero_incorrecto'
    tarjeta = tarjetas_validas[numero]
    if tarjeta['vencida']:
        return 'vencida'
    if tarjeta['codigo'] != codigo:
        return 'codigo_incorrecto'
    if tarjeta['titular'] != titular:
        return 'titular_incorrecto'
    if tarjeta['fondos'] < 20000:
        return 'fondos_insuficientes'
    return 'aprobado'

@login_required
def pagar_con_tarjeta(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)

    if request.method == 'POST':
        numero = request.POST.get('numero_tarjeta', '').strip()
        codigo = request.POST.get('codigo_seguridad', '').strip()
        titular = request.POST.get('titular', '').strip()

        try:
            resultado = simular_servidor_pago(numero, codigo, titular)
        except Exception:
            return render(request, 'pago/pagar_tarjeta.html', {
                'reserva': reserva,
                'error': 'Hubo un problema conectando al servidor de pago, intente mas tarde'
            })

        if resultado == 'aprobado':
            Pago.objects.create(
                reserva=reserva,
                monto=reserva.clase.actividad.precio,
                metodo_pago='tarjeta',
                estado_pago='aprobado',
            )
            reserva.estado = 'confirmada'
            reserva.save()
            return render(request, 'pago/pagar_tarjeta.html', {
                'reserva': reserva,
                'exito': 'Pago exitoso'
            })
        elif resultado == 'numero_incorrecto':
            error = 'El número de tarjeta es incorrecto'
        elif resultado == 'vencida':
            error = 'Tarjeta vencida'
        elif resultado == 'codigo_incorrecto':
            error = 'Código de seguridad incorrecto, vuelva a intentarlo'
        elif resultado == 'titular_incorrecto':
            error = 'Titular incorrecto'
        elif resultado == 'fondos_insuficientes':
            error = 'Fondos insuficientes'
        else:
            error = 'Hubo un problema conectando al servidor de pago, intente mas tarde'

        return render(request, 'pago/pagar_tarjeta.html', {
            'reserva': reserva,
            'error': error
        })

    return render(request, 'pago/pagar_tarjeta.html', {'reserva': reserva})


@login_required
def pagar_con_creditos(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)
    usuario = request.user
    precio_clase = reserva.clase.actividad.precio

    if request.method == 'POST':
        if usuario.creditos >= precio_clase:
            usuario.creditos -= precio_clase
            usuario.save()

            Pago.objects.create(
                reserva=reserva,
                monto=precio_clase,
                metodo_pago='creditos',
                estado_pago='aprobado',
            )
            reserva.estado = 'confirmada'
            reserva.save()

            messages.success(request, f"Pago exitoso. Se descontaron {precio_clase} créditos de tu cuenta.")
            return redirect('reservas')
        else:
            return render(request, 'pago/pagar_creditos.html', {
                'reserva': reserva,
                'creditos_usuario': usuario.creditos,
                'precio_clase': precio_clase,
                'creditos_restantes': 0,
                'error': 'No tiene suficientes créditos para esta clase'
            })

    creditos_restantes = usuario.creditos - precio_clase if usuario.creditos >= precio_clase else 0

    return render(request, 'pago/pagar_creditos.html', {
        'reserva': reserva,
        'creditos_usuario': usuario.creditos,
        'precio_clase': precio_clase,
        'creditos_restantes': creditos_restantes,
    })