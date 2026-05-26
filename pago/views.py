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




@login_required
def pagar_con_mercadopago(request, reserva_id):
    # 1. Volvemos a instanciar el SDK acá adentro (como hizo tu compañero por seguridad)
    sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)

    reserva = get_object_or_404(
        Reserva,
        id=reserva_id,
        usuario=request.user
    )

    # 2. Mantenemos tu validación pero corregida al estado real ('pendiente')
    if reserva.estado != 'pendiente':
        messages.warning(request, "La reserva ya fue abonada o no está disponible para pagar.")
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
            # Usamos la URL limpia que maneja tu archivo views.py
            "success": f"{settings.NGROK_URL}/pago/exito/", 
            "failure": f"{settings.NGROK_URL}/pago/fallo/",
            "pending": f"{settings.NGROK_URL}/pago/pendiente/",
        },
        "auto_return": "approved",
        "notification_url": f"{settings.NGROK_URL}/pago/webhook/"
    }

    # 3. Usamos la llamada directa que tenías vos (si falla, usás la de él en dos líneas)
    preference_response = sdk.preference().create(preference_data)
    
    print("=== MERCADOPAGO DEBUG ===")
    print(f"Status: {preference_response.get('status')}")
    print("=========================")

    if preference_response["status"] not in [200, 201]:
        pago.delete()
        messages.error(request, "No fue posible conectarse con la billetera virtual. Intente nuevamente más tarde")
        return redirect('detalle_reserva', reserva_id=reserva.id)

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
    external_reference = request.GET.get('external_reference')
    payment_id = request.GET.get('payment_id')

    pago_confirmado = False

    if external_reference:
        try:
            pago = Pago.objects.get(id=external_reference)
            pago.estado_pago = 'aprobado'
            pago.payment_id = payment_id
            pago.save()
            pago.reserva.estado = 'confirmada'
            pago.reserva.save()
            pago_confirmado = True
        except Pago.DoesNotExist:
            pass

    if not pago_confirmado and payment_id:
        pago = Pago.objects.filter(
            reserva__usuario=request.user,
            estado_pago='pendiente',
            metodo_pago='mercado_pago'
        ).order_by('-fecha_pago').first()

        if pago:
            try:
                payment_response = sdk.payment().get(payment_id)
                if payment_response.get('status') in [200, 201]:
                    payment_data = payment_response.get('response', {})
                    if payment_data.get('status') == 'approved':
                        pago.estado_pago = 'aprobado'
                        pago.payment_id = payment_id
                        pago.save()
                        pago.reserva.estado = 'confirmada'
                        pago.reserva.save()
                        pago_confirmado = True
            except Exception:
                pass

    if pago_confirmado:
        messages.success(request, "¡Pago exitoso! Tu reserva ha sido confirmada.")
    else:
        messages.warning(request, "No pudimos confirmar el pago automáticamente. Si pagaste, la confirmación llegará en unos minutos.")

    return redirect('reservas')


@login_required
def pago_fallo(request):
    external_reference = request.GET.get('external_reference')
    if external_reference:
        try:
            pago = Pago.objects.get(id=external_reference)
            pago.estado_pago = 'rechazado'
            pago.save()
        except Pago.DoesNotExist:
            pass
    messages.error(request, "Pago rechazado")
    return redirect('reservas')


def pago_pendiente(request):
    external_reference = request.GET.get('external_reference')
    if external_reference:
        try:
            pago = Pago.objects.get(id=external_reference)
            pago.estado_pago = 'pendiente'
            pago.save()
        except Pago.DoesNotExist:
            pass
    messages.warning(request, "Tu pago está pendiente de confirmación.")
    return redirect('reservas')