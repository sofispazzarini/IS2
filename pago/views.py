import mercadopago
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from turno.models import Reserva, Actividad, Clase
from turno.models import Abono, TurnoFijo
from django.utils import timezone
from django.db.models import Q
from .models import Pago
from .forms import CompraPaqueteForm
from user.models import Penalizacion

sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)


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
            return redirect('reservas')
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
    sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)

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
                "unit_price": 1000.0
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

    #pago.preference_id = preference["id"]
    pago.preference_id = preference.get("id", "")
    pago.save()

    #return redirect(preference["init_point"])
    init_point = preference.get("init_point") or preference.get("sandbox_init_point")

    if not init_point:
      return HttpResponse("No se pudo generar link de pago", status=500)

    return redirect(init_point)

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

    estado_mp = payment_data.get("status")

    if external_reference.startswith("abono_"):
        from turno.models import Abono, TurnoFijo, Reserva as Reserva_
        from turno.views import _calcular_info_abono, _calcular_info_abono_para_turnos, _crear_reservas_abono
        try:
            abono_id = int(external_reference.replace("abono_", ""))
            abono = Abono.objects.get(id=abono_id)
            abono.payment_id = payment_id

            if estado_mp == "approved":
                # Flujo hacerse_abonado / abonar_nuevo_turno_fijo: crear TurnoFijo desde reservas origen
                nuevos_tf_ids = []
                if abono.reservas_origen_ids:
                    ids = [int(x) for x in abono.reservas_origen_ids.split(',') if x]
                    for r in Reserva_.objects.filter(id__in=ids).select_related('clase', 'clase__actividad'):
                        tf, _ = TurnoFijo.objects.get_or_create(
                            usuario=abono.usuario,
                            dia_semana=r.clase.fecha.weekday(),
                            hora_inicio=r.clase.hora_inicio,
                            defaults={'actividad': r.clase.actividad, 'activo': True},
                        )
                        nuevos_tf_ids.append(tf.id)

                # Combinar con turnos_fijos_ids del flujo abonar_mes
                existing_tf_ids = set()
                if abono.turnos_fijos_ids:
                    existing_tf_ids = {int(x) for x in abono.turnos_fijos_ids.split(',') if x}
                all_tf_ids = existing_tf_ids | set(nuevos_tf_ids)

                if all_tf_ids:
                    abono.turnos_fijos_ids = ','.join(str(x) for x in all_tf_ids)

                # Calcular monto definitivo y generar reservas
                if all_tf_ids:
                    info = _calcular_info_abono_para_turnos(
                        abono.usuario, list(all_tf_ids), abono.mes, abono.anio
                    )
                else:
                    info = _calcular_info_abono(abono.usuario, abono.mes, abono.anio)

                if info:
                    abono.cantidad_turnos_fijos = len(info['turnos_fijos'])
                    abono.descuento_porcentaje = info['descuento_porcentaje']
                    abono.monto_total = info['monto_total']
                    abono.monto_final = info['monto_final']
                    abono.estado_pago = 'aprobado'
                    abono.save()
                    _crear_reservas_abono(abono.usuario, abono, info)
                else:
                    abono.estado_pago = 'aprobado'
                    abono.save()

            elif estado_mp == "rejected":
                abono.estado_pago = 'rechazado'
                abono.save()

        except (Abono.DoesNotExist, ValueError):
            pass

    else:
        # Pago de clase suelta — lógica original sin cambios
        try:
            pago = Pago.objects.get(id=external_reference)

            pago.payment_id = payment_id

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
    payment_id = request.GET.get('payment_id')

    if payment_id:
        payment_response = sdk.payment().get(payment_id)
        payment_data = payment_response.get("response", {})

        if payment_data.get("status") == "approved":
            external_reference = payment_data.get("external_reference")
            try:
                pago = Pago.objects.get(id=external_reference)
                if pago.estado_pago != 'aprobado':
                    pago.payment_id = payment_id
                    pago.estado_pago = 'aprobado'
                    pago.save()

                    reserva = pago.reserva
                    reserva.estado = 'confirmada'
                    reserva.save()

                messages.success(request, "¡Pago exitoso! Tu reserva ha sido confirmada.")
                return redirect('detalle_reserva', reserva_id=pago.reserva.id)
            except Pago.DoesNotExist:
                pass

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
        monto_devolver = reserva.monto_pagado if reserva.monto_pagado is not None else reserva.clase.actividad.precio
        usuario.creditos += monto_devolver
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

@login_required
def comprar_paquete(request):
    usuario = request.user

    if request.method == 'POST':
        form = CompraPaqueteForm(request.POST)
        if form.is_valid():
            total_clases = 0
            subtotal = Decimal('0.00')
            items_comprados = []

            # 1. Recorrer los campos para calcular totales y días
            for campo, valor in form.cleaned_data.items():
                if campo.startswith('actividad_') and valor > 0:
                    actividad_id = campo.split('_')[1]
                    actividad = Actividad.objects.get(id=actividad_id)
                    cantidad = valor

                    # Obtener días seleccionados para esta actividad
                    dias_key = f'dias_{actividad_id}'
                    dias = form.cleaned_data.get(dias_key, [])

                    total_clases += cantidad
                    subtotal += actividad.precio * cantidad
                    items_comprados.append({
                        'actividad': actividad,
                        'cantidad': cantidad,
                        'dias': dias
                    })

            if total_clases == 0:
                messages.error(request, "Tenés que seleccionar al menos 1 clase para armar un paquete.")
                return render(request, 'pago/comprar_paquete.html', {'form': form, 'usuario': usuario})

            # 2. Aplicar Reglas de Negocio (Descuentos)
            descuento_porcentaje = 0

            usuario_penalizado = Penalizacion.objects.filter(usuario=usuario, activa=True).exists()

            if usuario_penalizado:
                descuento_porcentaje = 0
                messages.warning(request, "No se aplicaron descuentos promocionales debido a una penalización activa en tu cuenta.")
            else:
                if total_clases == 2:
                    descuento_porcentaje = 10
                elif total_clases >= 3:
                    descuento_porcentaje = 20

            monto_descuento = subtotal * Decimal(descuento_porcentaje / 100)
            total_final = subtotal - monto_descuento

            # 3. Guardar en sesión los datos de la compra
            request.session['paquete_compra'] = {
                'total_final': float(total_final),
                'subtotal': float(subtotal),
                'descuento': float(monto_descuento),
                'porcentaje_aplicado': descuento_porcentaje,
                'items': [{
                    'actividad_id': item['actividad'].id,
                    'cantidad': item['cantidad'],
                    'dias': item['dias']
                } for item in items_comprados]
            }

            return redirect('confirmar_pago_paquete')

    else:
        form = CompraPaqueteForm()

    # Obtener clases futuras no canceladas
    clases_futuras = Clase.objects.filter(
        fecha__gte=timezone.now().date(),
        cancelada=False,
        actividad__isnull=False
    ).select_related('actividad')

    # Nombres de días
    DIAS_NOMBRE = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

    # Construir diccionario de actividades con sus horarios disponibles
    actividades_con_horarios = {}
    for clase in clases_futuras:
        act_id = clase.actividad.id
        dia_semana = clase.fecha.weekday()  # 0=Lunes, 6=Domingo
        hora = clase.hora_inicio.strftime('%H:%M')

        if act_id not in actividades_con_horarios:
            actividades_con_horarios[act_id] = {
                'actividad': clase.actividad,
                'horarios': set()
            }
        # Guardar tupla (día, hora) como string único para el value del checkbox
        actividades_con_horarios[act_id]['horarios'].add((dia_semana, hora))

    # Convertir a lista con horarios formateados
    actividades_disponibles = []
    for data in actividades_con_horarios.values():
        horarios_lista = []
        for dia, hora in sorted(data['horarios']):
            horarios_lista.append({
                'value': f"{dia}_{hora}",
                'label': f"{DIAS_NOMBRE[dia]} {hora}"
            })
        actividades_disponibles.append({
            'actividad': data['actividad'],
            'horarios': horarios_lista
        })

    # Ordenar por nombre de actividad
    actividades_disponibles.sort(key=lambda x: x['actividad'].nombre)

    return render(request, 'pago/comprar_paquete.html', {
        'form': form,
        'usuario': usuario,
        'actividades_disponibles': actividades_disponibles
    })

@login_required
def confirmar_pago_paquete(request):
    datos_paquete = request.session.get('paquete_compra')
    if not datos_paquete:
        messages.error(request, "No hay ninguna compra de paquete activa.")
        return redirect('comprar_paquete')

    if request.method == 'POST':
        sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
        usuario = request.user

        preference_data = {
            "items": [
                {
                    "title": "Paquete de clases",
                    "quantity": 1,
                    "currency_id": "ARS",
                    "unit_price": float(datos_paquete['total_final'])
                }
            ],
            "external_reference": f"paquete_{usuario.id}",
            "back_urls": {
                "success": f"{settings.NGROK_URL}/pago/paquete/exito/",
                "failure": f"{settings.NGROK_URL}/pago/paquete/fallo/",
                "pending": f"{settings.NGROK_URL}/pago/paquete/pendiente/",
            },
            "auto_return": "approved",
            "notification_url": f"{settings.NGROK_URL}/pago/webhook/",
        }

        preference_response = sdk.preference().create(preference_data)
        preference = preference_response["response"]

        init_point = preference.get("init_point") or preference.get("sandbox_init_point")

        if not init_point:
            messages.error(request, "No se pudo generar el enlace de pago.")
            return redirect('comprar_paquete')

        return redirect(init_point)

    return render(request, 'pago/confirmar_pago_paquete.html', {'paquete': datos_paquete})


@login_required
def paquete_exito(request):
    """Callback de éxito de MercadoPago para paquetes."""
    from datetime import time

    datos_paquete = request.session.get('paquete_compra')
    if not datos_paquete:
        messages.info(request, "El paquete ya fue procesado.")
        return redirect('reservas')

    usuario = request.user
    turnos_creados = 0

    for item in datos_paquete['items']:
        actividad = Actividad.objects.get(id=item['actividad_id'])
        usuario.creditos += (actividad.precio * item['cantidad'])

        # Crear TurnoFijo si hay días seleccionados
        dias = item.get('dias', [])
        for dia in dias:
            TurnoFijo.objects.get_or_create(
                usuario=usuario,
                actividad=actividad,
                dia_semana=int(dia),
                hora_inicio=time(10, 0),
                defaults={'activo': True}
            )
            turnos_creados += 1

    usuario.save()

    del request.session['paquete_compra']

    if turnos_creados > 0:
        messages.success(request, f"¡Paquete comprado con éxito! Los créditos fueron acreditados y se crearon {turnos_creados} turno(s) fijo(s).")
    else:
        messages.success(request, "¡Paquete comprado con éxito! Los créditos fueron acreditados en tu cuenta.")
    return redirect('reservas')


@login_required
def paquete_fallo(request):
    """Callback de fallo de MercadoPago para paquetes."""
    messages.error(request, "El pago no pudo ser procesado. Intenta nuevamente.")
    return redirect('confirmar_pago_paquete')


@login_required
def paquete_pendiente(request):
    """Callback de pago pendiente de MercadoPago para paquetes."""
    messages.warning(request, "El pago está pendiente de confirmación. Te notificaremos cuando se acredite.")
    return redirect('reservas')