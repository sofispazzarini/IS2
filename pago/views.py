import mercadopago
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from turno.models import Reserva
from .models import Pago

#sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
print(settings.MERCADO_PAGO_ACCESS_TOKEN)




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
def pagar_con_mercadopago(request, reserva_id):

    reserva = get_object_or_404(
        Reserva,
        id=reserva_id,
        usuario=request.user
    )

    if reserva.estado != 'pendiente_pago':
        messages.warning(request, "La reserva ya fue abonada.")
        return redirect('detalle_reserva', reserva_id=reserva.id)

    pago = Pago.objects.create(
        reserva=reserva,
        monto=reserva.clase.actividad.precio,
        metodo_pago='mercado_pago',
        estado_pago='pendiente'
    )

    preference_data = {
        "items": [
            {
                "title": f"Clase de {reserva.clase.actividad.nombre}",
                "quantity": 1,
                "currency_id": "ARS",
                "unit_price": float(pago.monto)
            }
        ],
        "external_reference": str(pago.id),
        "back_urls": {
            "success": f"{settings.NGROK_URL}/pago/exito/",
            "failure": f"{settings.NGROK_URL}/pago/fallo/",
            "pending": f"{settings.NGROK_URL}/pago/pendiente/",
        },
        "auto_return": "approved",
        "notification_url": f"{settings.NGROK_URL}/pago/webhook/",
    }

    preference_response = sdk.preference().create(preference_data)
    preference = preference_response["response"]

    pago.preference_id = preference["id"]
    pago.save()

    return redirect(preference["init_point"])

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
    
@csrf_exempt
def webhook_mercadopago(request):

    if request.method != "POST":
        return HttpResponse(status=400)

    payment_id = request.GET.get("data.id")

    if not payment_id:
        return HttpResponse(status=400)

    payment_response = sdk.payment().get(payment_id)
    payment_data = payment_response["response"]

    external_reference = payment_data.get("external_reference")

    if not external_reference:
        return HttpResponse(status=400)

    try:
        pago = Pago.objects.get(id=external_reference)

        pago.payment_id = payment_id

        estado_mp = payment_data.get("status")

        if estado_mp == "approved":

            pago.estado_pago = "aprobado"

            reserva = pago.reserva
            reserva.estado = "confirmada"
            reserva.save()

        elif estado_mp == "rejected":
            pago.estado_pago = "rechazado"

        pago.save()

    except Pago.DoesNotExist:
        pass

    return HttpResponse(status=200)

@login_required
def pago_exito(request):
    messages.success(request, "¡Pago exitoso! Tu reserva ha sido confirmada.")
    return redirect('reservas')

@login_required
def pago_fallo(request):
    messages.error(request, "El pago ha fallado. Por favor, intenta nuevamente.")
    return redirect('reservas')

@login_required
def pago_pendiente(request):
    messages.warning(request, "Tu pago está pendiente de confirmación.")
    return redirect('reservas')

@login_required
def acumular_creditos(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)
    usuario = request.user

    if reserva.estado == 'cancelada':
        usuario.creditos += reserva.clase.actividad.precio
        usuario.save()
        messages.success(request, f"Se han acumulado {reserva.clase.actividad.precio} créditos en tu cuenta.")
    else:
        messages.error(request, "Solo se pueden acumular créditos de reservas canceladas.")

    return redirect('reservas')

@login_required
def solicitar_reembolso(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)

    if reserva.estado == 'cancelada':
        messages.success(request, "Tu solicitud de reembolso ha sido enviada.")
    else:
        messages.error(request, "Solo se pueden solicitar reembolsos de reservas canceladas.")

    return redirect('reservas')