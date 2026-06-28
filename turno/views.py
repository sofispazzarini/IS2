
from datetime import datetime, timedelta
from datetime import timedelta
import io
import base64

import mercadopago
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import calendar
import qrcode

from .models import Clase, Reserva, ListaEspera, Asistencia, TurnoFijo, Abono, Salon
from .services import validar_qr
from .forms import ClaseForm
from pago.models import Pago
from actividad.models import Actividad
from user.models import Profesor, Penalizacion
from resena.models import Resena
from resena.forms import ResenaForm
from django.db.models import Avg, Count, Sum, Q

from django.urls import reverse

from django.db import transaction

from decimal import Decimal
from django.http import HttpResponse

def registrar_asistencia(request, qr_uuid):
    resultado = validar_qr(str(qr_uuid), registrado_por=request.user if request.user.is_authenticated else None)

    if resultado.exito:
        return HttpResponse("✔ Asistencia registrada correctamente")

    return HttpResponse(resultado.mensaje, status=400)


def generar_qr(request, obj_id):
    base_url = "https://supreme-cavalier-unchain.ngrok-free.dev"
    
    obj = Reserva.objects.get(id=obj_id)

    print(obj.qr_uuid) 
    
    url = f"{base_url}/asistencia/{obj.qr_uuid}/"
    print("URL DEL QR:", url)
    img = qrcode.make(url)
    img.save("qr.png")
  
    return HttpResponse("QR generado")
    
    

def es_admin(user):
    return user.rol in ('secretario', 'dueno')


def es_dueno(user):
    return user.rol == 'dueno'


@login_required
def mis_turnos(request):
    """Muestra los turnos/reservas próximas del usuario."""
    ahora = timezone.localtime(timezone.now())
    hoy = ahora.date()

    reservas = Reserva.objects.filter(
        usuario=request.user,
        clase__fecha__gte=hoy
    ).exclude(
        estado='cancelada'
    ).select_related('clase', 'clase__actividad', 'clase__profesor').order_by('clase__fecha', 'clase__hora_inicio')

    reservas_con_info = []
    for reserva in reservas:
        dias_anticipacion = (reserva.clase.fecha - hoy).days
        puede_cancelar = dias_anticipacion >= 2

        # Determinar si mostrar QR (30 min antes hasta fin de clase)
        mostrar_qr = False
        qr_image = None
        if reserva.estado == 'confirmada' and not reserva.qr_usado:
            clase = reserva.clase
            if clase.fecha == hoy:
                from datetime import datetime, timedelta
                hora_inicio = datetime.combine(hoy, clase.hora_inicio)
                hora_fin = datetime.combine(hoy, clase.hora_fin)
                ahora_dt = datetime.combine(hoy, ahora.time())
                ventana_inicio = hora_inicio - timedelta(minutes=30)

                if ventana_inicio <= ahora_dt <= hora_fin:
                    mostrar_qr = True
                    #qr_image = generar_qr_base64(str(reserva.qr_uuid))
                    base_url = " https://supreme-cavalier-unchain.ngrok-free.dev"
                    url = f"{base_url}/turno/asistencia/{reserva.qr_uuid}/"
                    qr_image = generar_qr_base64(url)

        reservas_con_info.append({
            'reserva': reserva,
            'puede_cancelar': puede_cancelar,
            'dias_anticipacion': dias_anticipacion,
            'mostrar_qr': mostrar_qr,
            'qr_image': qr_image,
        })

    tiene_turnos_fijos = False
    if request.user.rol == 'cliente':
        tiene_turnos_fijos = TurnoFijo.objects.filter(usuario=request.user, activo=True).exists()

    return render(request, 'turno/mis_turnos.html', {
        'reservas_con_info': reservas_con_info,
        'tiene_turnos': len(reservas_con_info) > 0,
        'tiene_turnos_fijos': tiene_turnos_fijos,
    })

@login_required
def lista_clases(request):
    """Vista de calendario para reservar clases."""
    hoy = timezone.localdate()
    year = int(request.GET.get('year', hoy.year))
    month = int(request.GET.get('month', hoy.month))

    actividades = Actividad.objects.filter(activa=True).order_by('nombre')
    profesores = Profesor.objects.filter(activo=True).order_by('apellido', 'nombre')

    return render(request, 'turno/calendario_clases.html', {
        'year': year,
        'month': month,
        'actividades': actividades,
        'profesores': profesores,
    })


@login_required
def calendario_api(request):
    """API que retorna clases agrupadas por día para el calendario."""
    hoy = timezone.localdate()
    year = int(request.GET.get('year', hoy.year))
    month = int(request.GET.get('month', hoy.month))
    actividad_id = request.GET.get('actividad')
    profesor_id = request.GET.get('profesor')
    horario = request.GET.get('horario')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')

    # Validación: fecha_desde no puede ser mayor a fecha_hasta
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        return JsonResponse({
            'year': year,
            'month': month,
            'dias': {},
            'mensaje_vacio': 'La fecha "desde" no puede ser mayor a la fecha "hasta"',
        })

    # OPTIMIZACIÓN: Se agregó 'salon' al select_related
    clases = Clase.objects.filter(
        cancelada=False,
    ).select_related('actividad', 'profesor', 'salon')

    # Aplicar filtro de rango de fechas O filtro por mes
    if fecha_desde or fecha_hasta:
        if fecha_desde:
            clases = clases.filter(fecha__gte=fecha_desde)
        if fecha_hasta:
            clases = clases.filter(fecha__lte=fecha_hasta)
    else:
        clases = clases.filter(fecha__year=year, fecha__month=month)

    if actividad_id:
        clases = clases.filter(actividad_id=actividad_id)
    if profesor_id:
        clases = clases.filter(profesor_id=profesor_id)
    if horario:
        clases = clases.filter(hora_inicio__hour=int(horario))

    dias = {}
    for clase in clases:
        fecha_str = clase.fecha.isoformat()
        reservas_activas = clase.reservas.exclude(estado='cancelada').count()
        cupos = clase.cupo_maximo - reservas_activas
        es_pasada = clase.fecha < hoy

        if fecha_str not in dias:
            dias[fecha_str] = []
        dias[fecha_str].append({
            'id': clase.id,
            'actividad': clase.actividad.nombre,
            'hora_inicio': clase.hora_inicio.strftime('%H:%M'),
            'hora_fin': clase.hora_fin.strftime('%H:%M'),
            'profesor': f"{clase.profesor.nombre} {clase.profesor.apellido}",
            'cupos': cupos,
            # CAMBIADO: Mandamos solo el string del nombre (o un texto seguro si no tiene)
            'salon': clase.salon.nombre if clase.salon else "Sin salón",
            'precio': float(clase.actividad.precio),
            'es_pasada': es_pasada,
        })

    for fecha in dias:
        dias[fecha].sort(key=lambda x: x['hora_inicio'])

    # Mensaje vacío cuando se filtra sin resultados
    mensaje_vacio = None
    if not dias:
        if fecha_desde or fecha_hasta:
            mensaje_vacio = "No hay actividades programadas para las fechas seleccionadas"
        elif horario:
            mensaje_vacio = "no existen actividades en el horario seleccionado"
        elif profesor_id:
            mensaje_vacio = "este profesor no tiene actividades programadas"

    return JsonResponse({
        'year': year,
        'month': month,
        'dias': dias,
        'mensaje_vacio': mensaje_vacio,
    })

@login_required
def pedir_turno(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id)
    usuario = request.user

    if request.method == 'POST':
        # 0. Verificar que la clase no haya pasado
        ahora = timezone.localtime(timezone.now())
        if clase.fecha < ahora.date():
            return render(request, 'turno/pedir_turno.html', {
                'clase': clase,
                'error': 'No se puede reservar una clase pasada.'
            })
        if clase.fecha == ahora.date() and clase.hora_inicio <= ahora.time():
            return render(request, 'turno/pedir_turno.html', {
                'clase': clase,
                'error': 'No se puede reservar una clase cuyo horario ya pasó.'
            })

        # 1. Escenario III: Superposición de turnos
        superposicion = Reserva.objects.filter(
            usuario=usuario,
            clase__fecha=clase.fecha,
            clase__hora_inicio__lt=clase.hora_fin,  # El inicio de la reservada es antes de que termine la nueva
            clase__hora_fin__gt=clase.hora_inicio,   # El fin de la reservada es después de que arranque la nueva
        ).exclude(estado='cancelada').exists()

        if superposicion:
            # Mandamos el error descriptivo al mismo template
            return render(request, 'turno/pedir_turno.html', {
                'clase': clase,
                'error': 'Ya tenés un turno reservado que se superpone con el horario de esta clase.'
            })

        # 2. Verificar cupo
        reservas_activas = Reserva.objects.filter(
            clase=clase
        ).exclude(estado='cancelada').count()

        if reservas_activas >= clase.cupo_maximo:
            # Escenario II: Lista de espera
            ListaEspera.objects.get_or_create(usuario=usuario, clase=clase)
            messages.info(request, "No hay cupos disponibles. Has sido agregado a la lista de espera.")
            return redirect('lista_clases')

        # 3. Escenario I: Reserva exitosa
        nueva_reserva = Reserva.objects.create(
            usuario=usuario,
            clase=clase,
            estado='pendiente_pago'
        )
        # IMPORTANTE: Pasamos el ID de la reserva a la página de éxito
        return redirect('reserva_exitosa', reserva_id=nueva_reserva.id)

    return render(request, 'turno/pedir_turno.html', {'clase': clase})

@login_required
def reserva_exitosa(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)
    qr_image = None
    if reserva.estado == 'confirmada':
        qr_data = str(reserva.qr_uuid)
        qr_image = generar_qr_base64(qr_data)
    return render(request, 'turno/reserva_exitosa.html', {
        'reserva': reserva,
        'qr_image': qr_image,
    })


@login_required
def detalle_reserva(request, reserva_id):
    """Vista de detalle de reserva para el cliente con opciones de pago y QR."""
    from datetime import datetime, timedelta

    reserva = get_object_or_404(
        Reserva.objects.select_related('clase', 'clase__actividad', 'clase__profesor'),
        id=reserva_id,
        usuario=request.user
    )

    ahora = timezone.localtime(timezone.now())
    hoy = ahora.date()
    clase = reserva.clase

    # Determinar si mostrar QR (30 min antes hasta fin de clase)
    mostrar_qr = False
    qr_image = None
    if reserva.estado == 'confirmada' and not reserva.qr_usado:
        if clase.fecha == hoy:
            hora_inicio = datetime.combine(hoy, clase.hora_inicio)
            hora_fin = datetime.combine(hoy, clase.hora_fin)
            ahora_dt = datetime.combine(hoy, ahora.time())
            ventana_inicio = hora_inicio - timedelta(minutes=30)

            if ventana_inicio <= ahora_dt <= hora_fin:
                mostrar_qr = True
                #qr_image = generar_qr_base64(str(reserva.qr_uuid))
                base_url = " https://supreme-cavalier-unchain.ngrok-free.dev"
                url = f"{base_url}/turno/asistencia/{reserva.qr_uuid}/"
                print("QR URL:", url)  # S

                qr_image = generar_qr_base64(url)

    # Determinar si puede cancelar (2 días de anticipación)
    dias_anticipacion = (clase.fecha - hoy).days
    puede_cancelar = dias_anticipacion >= 2

    return render(request, 'turno/detalle_reserva.html', {
        'reserva': reserva,
        'mostrar_qr': mostrar_qr,
        'qr_image': qr_image,
        'puede_cancelar': puede_cancelar,
        'dias_anticipacion': dias_anticipacion,
    })


@login_required
def cancelar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)
    clase = reserva.clase
    hoy = timezone.localdate()
    usuario = request.user

    # Calculamos si faltan menos de 2 días (48 horas) para la clase
    dias_anticipacion = (clase.fecha - hoy).days
    corresponde_penalizar = dias_anticipacion < 2

    if request.method == 'POST':
        with transaction.atomic():
            era_abonada = reserva.estado == 'confirmada'
            reserva.estado = 'cancelada'
            reserva.save()

            # ⚠️ ADAPTADO: Si cancela tarde, se crea una instancia en tu tabla Penalizacion
            if corresponde_penalizar:
                Penalizacion.objects.create(
                    usuario=usuario,
                    motivo=f"Cancelación tardía de la reserva #{reserva.id} para la clase de {clase.actividad.nombre}.",
                    activa=True
                )
                messages.warning(request, "Se aplicará una sanción a la hora de solicitar un pack de clases.")

            # =========================================================================
            # LÓGICA DE LISTA DE ESPERA MASIVA (El primero que acepta se lo queda)
            # =========================================================================
            from django.core.mail import send_mail
            from django.conf import settings
            
            usuarios_espera = ListaEspera.objects.filter(clase=clase).select_related('usuario')
            if usuarios_espera.exists():
                lista_emails = list(usuarios_espera.values_list('usuario__email', flat=True))
                base_url = getattr(settings, 'NGROK_URL', 'http://127.0.0.1:8000')
                link_aceptar = f"{base_url}/turno/clases/aceptar-cupo/{clase.id}/"
                
                asunto = f"¡Se liberó un cupo para {clase.actividad.nombre}!"
                mensaje = (
                    f"Hola,\n\nTe avisamos que se acaba de liberar un cupo para la clase de {clase.actividad.nombre}.\n"
                    f"Podés quedarte con el lugar haciendo clic acá:\n{link_aceptar}\n\n"
                    f"¡El primero que confirme se queda con el cupo!"
                )
                try:
                    send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, lista_emails, fail_silently=False)
                except Exception as e:
                    print(f"Error al enviar correos: {e}")
            # =========================================================================

        # Mantenemos tu flujo de redirección y reembolsos intacto
        if era_abonada:
            return redirect('opciones_reembolso', reserva_id=reserva.id)
        else:
            messages.success(request, "Reserva cancelada exitosamente.")
            return redirect('reservas')

    # Pasamos 'corresponde_penalizar' al template para mostrar el cartel de advertencia
    return render(request, 'turno/confirmar_cancelacion.html', {
        'reserva': reserva,
        'corresponde_penalizar': corresponde_penalizar
    })


@login_required
def opciones_reembolso(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user, estado='cancelada')
    pago = reserva.pagos.filter(estado_pago='aprobado').first()
    # Después:
    monto = reserva.monto_pagado if reserva.monto_pagado is not None else (pago.monto if pago else reserva.clase.actividad.precio)

    return render(request, 'turno/opciones_reembolso.html', {
        'reserva': reserva,
        'pago': pago,
        'monto': monto
    })


@login_required
def admin_clases(request):
    """Panel de administración de clases para secretarios y dueños."""
    if not es_admin(request.user):
        messages.error(request, "No tienes permisos para acceder a esta sección.")
        return redirect('core:home')

    actividad_id = request.GET.get('actividad', '')
    profesor_id = request.GET.get('profesor', '')
    estado = request.GET.get('estado', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    salon_id = request.GET.get('salon', '')

    clases = Clase.objects.filter(fecha__gte=timezone.localdate())

    if actividad_id:
        clases = clases.filter(actividad_id=actividad_id)
    if profesor_id:
        clases = clases.filter(profesor_id=profesor_id)
    if estado == 'activas':
        clases = clases.filter(cancelada=False)
    elif estado == 'canceladas':
        clases = clases.filter(cancelada=True)
    if fecha_desde:
        clases = clases.filter(fecha__gte=fecha_desde)
    if fecha_hasta:
        clases = clases.filter(fecha__lte=fecha_hasta)
    if salon_id:
        clases = clases.filter(salon_id=salon_id)

    clases = clases.order_by('fecha', 'hora_inicio').select_related('actividad', 'profesor')

    return render(request, 'turno/admin_clases.html', {
        'clases': clases,
        'es_dueno': es_dueno(request.user),
        'actividades': Actividad.objects.filter(activa=True).order_by('nombre'),
        'profesores': Profesor.objects.filter(activo=True).order_by('apellido', 'nombre'),
        'salones': Salon.objects.all().order_by('nombre'),
        'filtro_actividad': actividad_id,
        'filtro_profesor': profesor_id,
        'filtro_estado': estado,
        'filtro_fecha_desde': fecha_desde,
        'filtro_fecha_hasta': fecha_hasta,
        'filtro_salon': salon_id,
        'hay_filtros': any([actividad_id, profesor_id, estado, fecha_desde, fecha_hasta, salon_id]),
    })


@login_required
def crear_clase(request):
    """Crear una nueva clase (secretario o dueño)."""
    if not es_admin(request.user):
        messages.error(request, "No tienes permisos para crear clases.")
        return redirect('core:home')

    if request.method == 'POST':
        form = ClaseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Clase creada con éxito.")
            return redirect('admin_clases')
    else:
        form = ClaseForm()

    return render(request, 'turno/crear_clase.html', {'form': form})


@login_required
def modificar_clase(request, clase_id):
    """Modificar una clase existente (solo dueño)."""
    if not es_dueno(request.user):
        messages.error(request, "Solo el dueño puede modificar clases.")
        return redirect('admin_clases')

    clase = get_object_or_404(Clase, id=clase_id)

    if request.method == 'POST':
        form = ClaseForm(request.POST, instance=clase)
        if form.is_valid():
            form.save()
            messages.success(request, "Clase modificada con éxito.")
            return redirect('admin_clases')
    else:
        form = ClaseForm(instance=clase)

    return render(request, 'turno/modificar_clase.html', {'form': form, 'clase': clase})


@login_required
def cancelar_clase(request, clase_id):
    """Cancelar una clase y notificar a los usuarios inscriptos con link de devolución (solo dueño)."""
    if not es_dueno(request.user):
        messages.error(request, "Solo el dueño puede cancelar clases.")
        return redirect('admin_clases')

    clase = get_object_or_404(Clase, id=clase_id)

    if request.method == 'POST':
        todas_las_reservas = Reserva.objects.filter(
            clase=clase
        ).exclude(estado='cancelada').select_related('usuario')

        reservas_confirmadas = todas_las_reservas.filter(estado='confirmada')
        emails_enviados = 0
        for reserva in reservas_confirmadas:
            usuario = reserva.usuario
            reserva.estado = 'cancelada'
            reserva.save()

            if usuario.notificaciones_activas and usuario.email:
                link = f"{settings.NGROK_URL}/turno/reservas/{reserva.id}/opciones-reembolso/"
                try:
                    send_mail(
                        subject=f"Clase cancelada: {clase.actividad.nombre}",
                        message=(
                            f"Hola {usuario.first_name or usuario.username},\n\n"
                            f"La clase fue cancelada.\n\n"
                            f"Detalles de la clase:\n"
                            f"- Actividad: {clase.actividad.nombre}\n"
                            f"- Fecha: {clase.fecha.strftime('%d/%m/%Y')}\n"
                            f"- Horario: {clase.hora_inicio.strftime('%H:%M')} hs\n\n"
                            f"Hacé clic aquí para gestionar tu devolución:\n"
                            f"{link}\n\n"
                            f"Disculpá las molestias.\n\n"
                            f"Saludos,\nEquipo SIRCA"
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[usuario.email],
                        fail_silently=True,
                    )
                    emails_enviados += 1
                except Exception:
                    pass

        todas_las_reservas.update(estado='cancelada')
        Clase.objects.filter(pk=clase.pk).update(cancelada=True)

        messages.success(
            request,
            f"Clase cancelada. Se notificó a {emails_enviados} usuario(s) con reserva confirmada."
        )
        return redirect('admin_clases')

    reservas_count = Reserva.objects.filter(
        clase=clase
    ).exclude(estado='cancelada').count()

    return render(request, 'turno/confirmar_cancelar_clase.html', {
        'clase': clase,
        'reservas_count': reservas_count,
    })

@login_required
def detalle_clase(request, clase_id):
    """Vista detallada de una clase para administradores."""
    if not es_admin(request.user):
        messages.error(request, "No tienes permisos para acceder a esta sección.")
        return redirect('core:home')

    clase = get_object_or_404(
        Clase.objects.select_related('actividad', 'profesor'),
        id=clase_id
    )

    todas_reservas = Reserva.objects.filter(clase=clase).select_related('usuario').order_by('-fecha_reserva')
    reservas_activas = todas_reservas.exclude(estado='cancelada')
    reservas_canceladas = todas_reservas.filter(estado='cancelada')
    asistencias = todas_reservas.filter(estado='asistida').select_related('asistencia')

    lista_espera_usuarios = ListaEspera.objects.filter(clase=clase).select_related('usuario').order_by('fecha_ingreso')
    cant_espera = lista_espera_usuarios.count()
    
    pagos = Pago.objects.filter(reserva__clase=clase).select_related('reserva__usuario').order_by('-fecha_pago')

    resenas = Resena.objects.filter(clase=clase).select_related('usuario').order_by('-fecha')[:5]

    promedio_resenas = Resena.objects.filter(clase=clase).aggregate(promedio=Avg('puntuacion'))['promedio']

    stats = todas_reservas.aggregate(
        total=Count('id'),
        confirmadas=Count('id', filter=Q(estado='confirmada')),
        pendientes=Count('id', filter=Q(estado='pendiente_pago')),
        canceladas=Count('id', filter=Q(estado='cancelada')),
        asistidas=Count('id', filter=Q(estado='asistida')),
    )

    cupos_disponibles = clase.cupo_maximo - (stats['confirmadas'] + stats['pendientes'])

    total_recaudado = pagos.filter(estado_pago='aprobado').aggregate(total=Sum('monto'))['total'] or 0

    ahora = timezone.localtime()
    clase_finalizada = (ahora.date() > clase.fecha) or (
        ahora.date() == clase.fecha and ahora.time() >= clase.hora_fin
    )
    clase_finalizada = clase_finalizada and not clase.cancelada

    inicio_clase_dt = timezone.make_aware(datetime.combine(clase.fecha, clase.hora_inicio))
    fin_ventana_dt = inicio_clase_dt + timedelta(hours=1,minutes=30)
    puede_registrar_asistencia = (inicio_clase_dt - timedelta(minutes=30))<= ahora <= fin_ventana_dt
    return render(request, 'turno/detalle_clase.html', {
        'clase': clase,
        'reservas_activas': reservas_activas,
        'reservas_canceladas': reservas_canceladas,
        'lista_espera_usuarios': lista_espera_usuarios,
        'cant_espera': cant_espera,
        'asistencias': asistencias,
        'pagos': pagos,
        'resenas': resenas,
        'promedio_resenas': promedio_resenas,
        'stats': stats,
        'cupos_disponibles': cupos_disponibles,
        'total_recaudado': total_recaudado,
        'clase_finalizada': clase_finalizada,
        'puede_registrar_asistencia': puede_registrar_asistencia,
        'es_dueno': es_dueno(request.user),
        'es_admin': es_admin(request.user),
    })

@login_required
def lista_presentes_clase(request, clase_id):
    """Mostrar la lista de presentes de una clase solo para secretario/dueno."""
    if not es_admin(request.user):
        messages.error(request, "No tienes permisos para ver la lista de presentes.")
        return redirect('core:home')

    clase = get_object_or_404(
        Clase.objects.select_related('actividad', 'profesor'),
        id=clase_id
    )

    ahora = timezone.localtime()
    clase_finalizada = (ahora.date() > clase.fecha) or (
        ahora.date() == clase.fecha and ahora.time() >= clase.hora_fin
    )
    clase_finalizada = clase_finalizada and not clase.cancelada

    if not clase_finalizada:
        messages.error(request, "La lista de presentes solo está disponible para clases finalizadas.")
        return redirect('detalle_clase', clase_id=clase.id)

    presentes = Reserva.objects.filter(
        clase=clase,
        estado='asistida'
    ).select_related('usuario').order_by('usuario__last_name', 'usuario__first_name')

    return render(request, 'turno/lista_presentes.html', {
        'clase': clase,
        'presentes': presentes,
    })


@login_required
def ver_clase(request, clase_id):
    """Vista pública de detalle de clase para usuarios normales."""
    clase = get_object_or_404(
        Clase.objects.select_related('actividad', 'profesor'),
        id=clase_id
    )

    resenas = Resena.objects.filter(
        clase=clase
    ).select_related('usuario').order_by('-fecha')

    promedio_resenas = resenas.aggregate(promedio=Avg('puntuacion'))['promedio']
    total_resenas = resenas.count()

    reservas_activas = Reserva.objects.filter(clase=clase).exclude(estado='cancelada').count()
    cupos_disponibles = clase.cupo_maximo - reservas_activas

    ahora = timezone.localtime()
    clase_finalizada = (ahora.date() > clase.fecha) or (
        ahora.date() == clase.fecha and ahora.time() >= clase.hora_fin
    )
    clase_finalizada = clase_finalizada and not clase.cancelada

    usuario_tiene_reserva = Reserva.objects.filter(
        usuario=request.user,
        clase=clase
    ).exclude(estado='cancelada').exists()

    usuario_asistio = Reserva.objects.filter(
        usuario=request.user,
        clase=clase,
        estado='asistida'
    ).exists()

    resena_usuario = Resena.objects.filter(
        usuario=request.user,
        clase=clase
    ).first()

    en_lista_espera = ListaEspera.objects.filter(
        usuario=request.user, 
        clase=clase
    ).exists()

    form = ResenaForm()

    if request.method == 'POST' and 'crear_resena' in request.POST:
        form = ResenaForm(request.POST)
        if not usuario_asistio:
            messages.error(request, 'Solo quienes asistieron a esta clase pueden dejar una reseña.')
        elif not clase_finalizada:
            messages.error(request, 'La clase debe haber finalizado antes de poder dejar la reseña.')
        elif form.is_valid():
            resena = form.save(commit=False)
            resena.usuario = request.user
            resena.actividad = clase.actividad
            resena.clase = clase
            resena.puntuacion = int(request.POST.get('puntuacion', 5))
            resena.save()
            messages.success(request, 'Tu reseña fue enviada exitosamente.')
            return redirect('ver_clase', clase_id=clase.id)

    return render(request, 'turno/ver_clase.html', {
        'clase': clase,
        'resenas': resenas,
        'promedio_resenas': promedio_resenas,
        'total_resenas': total_resenas,
        'cupos_disponibles': cupos_disponibles,
        'usuario_tiene_reserva': usuario_tiene_reserva,
        'usuario_asistio': usuario_asistio,
        'clase_finalizada': clase_finalizada,
        'resena_usuario': resena_usuario,
        'en_lista_espera': en_lista_espera,
        'form': form,
    })


def generar_qr_base64(data):
    """Genera un código QR como imagen base64."""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_base64}"


@login_required
@require_http_methods(["POST"])
def validar_qr_api(request):
    """API para validar un código QR y frar asistencia."""
    if not es_admin(request.user):
        return JsonResponse({
            'exito': False,
            'mensaje': 'No tienes permisos para registrar asistencia.'
        }, status=403)

    qr_uuid = request.POST.get('qr_uuid', '').strip()
    if not qr_uuid:
        return JsonResponse({
            'exito': False,
            'mensaje': 'No se proporcionó código QR.'
        }, status=400)

    resultado = validar_qr(qr_uuid, registrado_por=request.user)

    response_data = {
        'exito': resultado.exito,
        'mensaje': resultado.mensaje,
    }

    if resultado.reserva:
        response_data['reserva'] = {
            'usuario': resultado.reserva.usuario.get_full_name() or resultado.reserva.usuario.username,
            'clase': str(resultado.reserva.clase),
            'estado': resultado.reserva.estado,
        }

    return JsonResponse(response_data)


@login_required
def escanear_qr(request):
    """Vista para que admins escaneen códigos QR."""
    if not es_admin(request.user):
        messages.error(request, "No tienes permisos para acceder a esta sección.")
        return redirect('core:home')

    resultado = None
    if request.method == 'POST':
        qr_uuid = request.POST.get('qr_uuid', '').strip()
        if qr_uuid:
            resultado = validar_qr(qr_uuid, registrado_por=request.user)

    return render(request, 'turno/escanear_qr.html', {
        'resultado': resultado,
    })


@login_required
@require_http_methods(["POST"])
def registrar_pago_presencial(request, reserva_id):
    """Registra un pago presencial para una reserva (solo admin)."""
    if not es_admin(request.user):
        messages.error(request, "No tienes permisos para registrar pagos.")
        return redirect('core:home')

    reserva = get_object_or_404(Reserva, id=reserva_id)

    if reserva.estado != 'pendiente_pago':
        messages.warning(request, "Esta reserva ya fue pagada o está cancelada.")
        return redirect('detalle_clase', clase_id=reserva.clase.id)

    metodo_pago = request.POST.get('metodo_pago', 'efectivo')
    metodos_validos = ['efectivo', 'posnet', 'transferencia']
    if metodo_pago not in metodos_validos:
        messages.error(request, "Método de pago inválido.")
        return redirect('detalle_clase', clase_id=reserva.clase.id)

    # Crear el pago
    from pago.models import Pago
    Pago.objects.create(
        reserva=reserva,
        monto=reserva.clase.actividad.precio,
        metodo_pago=metodo_pago,
        estado_pago='aprobado',
        registrado_por=request.user
    )

    # Actualizar estado de la reserva
    reserva.estado = 'confirmada'
    reserva.save()

    metodo_display = {'efectivo': 'efectivo', 'posnet': 'POSNET', 'transferencia': 'transferencia'}
    messages.success(request, f"Pago con {metodo_display.get(metodo_pago, metodo_pago)} registrado para {reserva.usuario.get_full_name() or reserva.usuario.username}.")
    return redirect('detalle_clase', clase_id=reserva.clase.id)


def registrar_asistencia_view(request, reserva_id):
    if request.method == "POST":
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        from django.core.exceptions import ValidationError
        from .services import registrar_asistencia_manual  
        from django.http import HttpResponseForbidden


        reserva = get_object_or_404(Reserva, id=reserva_id)
        try:
            registrar_asistencia_manual(reserva.id)
            messages.success(request, f"Asistencia registrada para {reserva.usuario.get_full_name()}")
        except ValidationError as e:
            messages.error(request, e.message)
           
        return redirect('detalle_clase', clase_id=reserva.clase.id)



@login_required
def panel_listas_espera(request):
    """Panel para que el staff vea las listas de espera de clases que no empezaron."""
    ahora = timezone.localtime(timezone.now())
    fecha_actual = ahora.date()
    hora_actual = ahora.time()

    # Filtramos las clases que todavía no arrancaron (futuras o de hoy más tarde)
    clases_activas = Clase.objects.filter(
        Q(fecha__gt=fecha_actual) | 
        Q(fecha=fecha_actual, hora_inicio__gt=hora_actual)
    ).select_related('actividad', 'profesor').order_by('fecha', 'hora_inicio')

    # Si querés, opcionalmente podemos precalculares el conteo de personas esperando a cada una
    for clase in clases_activas:
        clase.cant_espera = ListaEspera.objects.filter(clase=clase).count()

    return render(request, 'secretario/panel_listas_espera.html', {
        'clases': clases_activas,
    })

@login_required
def ver_detalle_espera(request, clase_id):
    """Detalle de una clase específica mostrando el orden de prioridad cronológico."""
    clase = get_object_or_404(Clase, id=clase_id)
    
    # REGLA DE NEGOCIO: Orden cronológico según fecha y hora en la que ingresaron
    espera_usuarios = ListaEspera.objects.filter(clase=clase).select_related('usuario').order_by('fecha_ingreso')
    
    return render(request, 'secretario/detalle_lista_espera.html', {
        'clase': clase,
        'espera_usuarios': espera_usuarios,
    })

@login_required 
def salir_lista_espera(request, clase_id):
    """Permite al usuario bajarse de la lista de espera de una clase."""
    if request.method == 'POST':
        registro = get_object_or_404(ListaEspera, clase_id=clase_id, usuario=request.user)
        registro.delete()
        messages.success(request, "Has salido de la lista de espera exitosamente.")

        # OPCIÓN A: Mandarlo a la lista general de clases/turnos del cliente
        return redirect('lista_clases')

    return redirect('lista_clases')


@login_required
def aceptar_cupo(request, clase_id):
    """Permite a usuario en lista de espera aceptar cupo disponible."""
    clase = get_object_or_404(Clase, id=clase_id)
    usuario = request.user

    # Verificar que la clase no haya pasado
    if clase.ya_paso:
        messages.error(request, "Esta clase ya ha pasado.")
        return redirect('reservas')

    # Verificar que usuario está en ListaEspera
    lista_espera = ListaEspera.objects.filter(usuario=usuario, clase=clase).first()
    if not lista_espera:
        messages.error(request, "No estás en la lista de espera de esta clase.")
        return redirect('reservas')

    # Verificar que hay cupo disponible
    reservas_activas = Reserva.objects.filter(
        clase=clase,
        estado__in=['confirmada', 'pendiente_pago']
    ).count()

    if reservas_activas >= clase.cupo_maximo:
        messages.error(request, "Lamentablemente, el cupo ya fue ocupado por otro usuario.")
        return redirect('reservas')

    # Verificar que no tenga ya una reserva
    reserva_existente = Reserva.objects.filter(usuario=usuario, clase=clase).first()
    if reserva_existente:
        messages.info(request, "Ya tienes una reserva para esta clase.")
        lista_espera.delete()
        return redirect('detalle_reserva', reserva_id=reserva_existente.id)

    # Crear Reserva con estado pendiente_pago
    reserva = Reserva.objects.create(
        usuario=usuario,
        clase=clase,
        estado='pendiente_pago'
    )

    # Eliminar de ListaEspera
    lista_espera.delete()

    messages.success(request, "¡Aceptaste el cupo! Ahora debes confirmar el pago.")

    # Redirigir al detalle de la reserva para pagar
    return redirect('detalle_reserva', reserva_id=reserva.id)


# ─── Helpers para el abono ────────────────────────────────────────────────────

def _fechas_del_mes_para_dia(dia_semana, mes, anio):
    """Retorna todas las fechas del mes donde fecha.weekday() == dia_semana (0=Lunes, 6=Domingo)."""
    from datetime import date, timedelta
    primer_dia = date(anio, mes, 1)
    total_dias = calendar.monthrange(anio, mes)[1]
    return [
        primer_dia + timedelta(days=d)
        for d in range(total_dias)
        if (primer_dia + timedelta(days=d)).weekday() == dia_semana
    ]

def _limpiar_turnos_fijos_no_pagados(usuario, hoy):
    """Elimina TurnoFijo sin Abono aprobado del mes actual. Ejecutar a partir del día 11."""
    if hoy.day < 11:
        return

    turnos_activos = TurnoFijo.objects.filter(usuario=usuario, activo=True)
    if not turnos_activos.exists():
        return

    abono_mes = Abono.objects.filter(
        usuario=usuario,
        mes=hoy.month,
        anio=hoy.year,
        estado_pago='aprobado',
    ).first()

    if not abono_mes:
        turnos_activos.delete()
        return

    ids_abonados = set(turnos_activos.values_list('id', flat=True))
    turnos_activos.exclude(id__in=ids_abonados).delete()

def _reservas_pendientes_sin_superposicion(usuario, hoy):
    """
    Devuelve reservas pendientes del mes que NO colisionan entre sí.
    Si dos reservas comparten weekday y sus ventanas de 1h se superponen, ambas se excluyen.
    """
    from datetime import datetime, timedelta
    import calendar as _cal

    ultimo_dia = hoy.replace(day=_cal.monthrange(hoy.year, hoy.month)[1])

    reservas = list(Reserva.objects.filter(
        usuario=usuario,
        estado='pendiente_pago',
        clase__fecha__gte=hoy,
        clase__fecha__lte=ultimo_dia,
    ).select_related('clase', 'clase__actividad').order_by('clase__fecha', 'clase__hora_inicio'))

    conflictivas = set()
    for i, ra in enumerate(reservas):
        for j, rb in enumerate(reservas):
            if i >= j:
                continue
            if ra.clase.fecha.weekday() != rb.clase.fecha.weekday():
                continue
            inicio_a = datetime.combine(hoy, ra.clase.hora_inicio)
            inicio_b = datetime.combine(hoy, rb.clase.hora_inicio)
            fin_a = inicio_a + timedelta(hours=1)
            fin_b = inicio_b + timedelta(hours=1)
            if inicio_a < fin_b and inicio_b < fin_a:
                conflictivas.add(ra.id)
                conflictivas.add(rb.id)

    return [r for r in reservas if r.id not in conflictivas]


def _calcular_info_abono_para_turnos(usuario, turno_fijo_ids, mes, anio):
    """Como _calcular_info_abono pero solo para los TurnoFijo con los IDs dados."""
    from datetime import date

    turnos_fijos = list(
        TurnoFijo.objects.filter(id__in=turno_fijo_ids, usuario=usuario, activo=True)
        .select_related('actividad')
    )
    if not turnos_fijos:
        return None

    next_month = mes + 1 if mes < 12 else 1
    next_year = anio if mes < 12 else anio + 1

    clases_por_turno = {}
    monto_total = Decimal('0')

    for turno in turnos_fijos:
        fechas_mes = _fechas_del_mes_para_dia(turno.dia_semana, mes, anio)
        clases_mes = list(Clase.objects.filter(
            actividad=turno.actividad,
            hora_inicio=turno.hora_inicio,
            fecha__in=fechas_mes,
            cancelada=False,
        ))
        fechas_sig = _fechas_del_mes_para_dia(turno.dia_semana, next_month, next_year)
        clases_extra = list(Clase.objects.filter(
            actividad=turno.actividad,
            hora_inicio=turno.hora_inicio,
            fecha__in=[f for f in fechas_sig if f.day <= 30],
            cancelada=False,
        ))
        todas = clases_mes + clases_extra
        clases_por_turno[turno.id] = todas
        monto_total += turno.actividad.precio * len(todas)

    n = len(turnos_fijos)
    descuento = 20 if n >= 3 else (10 if n == 2 else 0)
    factor = Decimal(str(1 - descuento / 100))
    monto_final = (monto_total * factor).quantize(Decimal('0.01'))
    monto_por_clase_por_turno = {
        t.id: (t.actividad.precio * factor).quantize(Decimal('0.01'))
        for t in turnos_fijos
    }

    return {
        'turnos_fijos': turnos_fijos,
        'clases_por_turno': clases_por_turno,
        'monto_total': monto_total,
        'descuento_porcentaje': descuento,
        'monto_final': monto_final,
        'monto_por_clase_por_turno': monto_por_clase_por_turno,
    }

def _calcular_info_abono(usuario, mes, anio):
    """
    Calcula precio, descuento y clases involucradas en el abono del mes.
    Retorna dict con toda la info, o None si el usuario no tiene turnos fijos activos.
    """
    from datetime import date

    turnos_fijos = list(
        TurnoFijo.objects.filter(usuario=usuario, activo=True).select_related('actividad')
    )
    if not turnos_fijos:
        return None

    next_month = mes + 1 if mes < 12 else 1
    next_year = anio if mes < 12 else anio + 1

    clases_por_turno = {}
    monto_total = Decimal('0')

    for turno in turnos_fijos:
        # Clases del mes actual que coinciden con el turno fijo
        fechas_mes = _fechas_del_mes_para_dia(turno.dia_semana, mes, anio)
        clases_mes = list(Clase.objects.filter(
            actividad=turno.actividad,
            hora_inicio=turno.hora_inicio,
            fecha__in=fechas_mes,
            cancelada=False,
        ))

        # Clases del 1 al 10 del mes siguiente
        fechas_sig = _fechas_del_mes_para_dia(turno.dia_semana, next_month, next_year)
        fechas_sig_1_10 = [f for f in fechas_sig if f.day <= 30]
        clases_extra = list(Clase.objects.filter(
            actividad=turno.actividad,
            hora_inicio=turno.hora_inicio,
            fecha__in=fechas_sig_1_10,
            cancelada=False,
        ))

        todas = clases_mes + clases_extra
        clases_por_turno[turno.id] = todas
        monto_total += turno.actividad.precio * len(todas)

    n = len(turnos_fijos)
    if n >= 3:
        descuento = 20
    elif n == 2:
        descuento = 10
    else:
        descuento = 0

    factor = Decimal(str(1 - descuento / 100))
    monto_final = (monto_total * factor).quantize(Decimal('0.01'))

    # Monto proporcional por clase (precio de la actividad con descuento aplicado)
    monto_por_clase_por_turno = {
        t.id: (t.actividad.precio * factor).quantize(Decimal('0.01'))
        for t in turnos_fijos
    }

    return {
        'turnos_fijos': turnos_fijos,
        'clases_por_turno': clases_por_turno,
        'monto_total': monto_total,
        'descuento_porcentaje': descuento,
        'monto_final': monto_final,
        'monto_por_clase_por_turno': monto_por_clase_por_turno,
    }


def _crear_reservas_abono(usuario, abono, info):
    """Crea una Reserva confirmada por cada clase del abono, sin duplicar."""
    for turno in info['turnos_fijos']:
        monto_pagado = info['monto_por_clase_por_turno'][turno.id]
        for clase in info['clases_por_turno'][turno.id]:
            ya_existe = Reserva.objects.filter(
                usuario=usuario, clase=clase
            ).exclude(estado='cancelada').exists()
            if not ya_existe:
                Reserva.objects.create(
                    usuario=usuario,
                    clase=clase,
                    estado='confirmada',
                    monto_pagado=monto_pagado,
                    abono=abono,
                )


# ─── Vistas del abono ─────────────────────────────────────────────────────────
@login_required
def abonar_mes(request):
    """Cliente abonado selecciona qué turnos fijos pagar este mes con MercadoPago (1-10)."""
    hoy = timezone.localdate()

    if not (1 <= hoy.day <= 30):
        messages.error(request, "El período de pago del abono es del 1 al 10 de cada mes.")
        return redirect('user:perfil')

    usuario = request.user

    if not TurnoFijo.objects.filter(usuario=usuario, activo=True).exists():
        messages.error(request, "No tenés turnos fijos activos.")
        return redirect('user:perfil')

    abono_aprobado = Abono.objects.filter(
        usuario=usuario, mes=hoy.month, anio=hoy.year, estado_pago='aprobado',
    ).first()

    ids_ya_abonados = set()
    if abono_aprobado:
        if abono_aprobado.turnos_fijos_ids:
            ids_ya_abonados = {int(x) for x in abono_aprobado.turnos_fijos_ids.split(',') if x}
        else:
            ids_ya_abonados = set(
                TurnoFijo.objects.filter(usuario=usuario, activo=True).values_list('id', flat=True)
            )

    turnos_pendientes = TurnoFijo.objects.filter(
        usuario=usuario, activo=True
    ).exclude(id__in=ids_ya_abonados).select_related('actividad')

    if not turnos_pendientes.exists():
        messages.info(request, "Ya pagaste el abono de todos tus turnos fijos este mes.")
        return redirect('user:perfil')

    if request.method == 'POST':
        turno_ids_raw = request.POST.getlist('turnos_fijos')
        if not turno_ids_raw:
            return render(request, 'turno/abonar_mes.html', {
                'turnos_pendientes': turnos_pendientes,
                'error': 'Seleccioná al menos un turno fijo para abonar.',
            })

        turno_ids = [int(t) for t in turno_ids_raw if t.isdigit()]
        info = _calcular_info_abono_para_turnos(usuario, turno_ids, hoy.month, hoy.year)

        if not info:
            return render(request, 'turno/abonar_mes.html', {
                'turnos_pendientes': turnos_pendientes,
                'error': 'No se encontraron clases para los turnos seleccionados.',
            })

        abono_existente = Abono.objects.filter(usuario=usuario, mes=hoy.month, anio=hoy.year).first()
        if abono_existente and abono_existente.estado_pago == 'aprobado':
            messages.info(request, "Ya pagaste el abono de este mes.")
            return redirect('user:perfil')

        if abono_existente:
            abono = abono_existente
            abono.turnos_fijos_ids = ','.join(str(t) for t in turno_ids)
            abono.cantidad_turnos_fijos = len(info['turnos_fijos'])
            abono.descuento_porcentaje = info['descuento_porcentaje']
            abono.monto_total = info['monto_total']
            abono.monto_final = info['monto_final']
            abono.metodo_pago = 'mercado_pago'
            abono.estado_pago = 'pendiente'
            abono.save()
        else:
            abono = Abono.objects.create(
                usuario=usuario,
                mes=hoy.month,
                anio=hoy.year,
                cantidad_turnos_fijos=len(info['turnos_fijos']),
                descuento_porcentaje=info['descuento_porcentaje'],
                monto_total=info['monto_total'],
                monto_final=info['monto_final'],
                metodo_pago='mercado_pago',
                estado_pago='pendiente',
                turnos_fijos_ids=','.join(str(t) for t in turno_ids),
            )

        sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
        preference_data = {
            "items": [{
                "title": f"Abono mensual {hoy.month}/{hoy.year} - SIRCA",
                "quantity": 1,
                "currency_id": "ARS",
                "unit_price": float(info['monto_final']),
            }],
            "external_reference": f"abono_{abono.id}",
            "back_urls": {
                "success": f"{settings.NGROK_URL}/turno/abono/exito/",
                "failure": f"{settings.NGROK_URL}/turno/abono/fallo/",
                "pending": f"{settings.NGROK_URL}/turno/abono/pendiente/",
            },
            "auto_return": "approved",
            "notification_url": f"{settings.NGROK_URL}/pago/webhook/",
        }

        preference_response = sdk.preference().create(preference_data)
        preference = preference_response.get("response", {})
        if "id" not in preference:
            return render(request, 'turno/abonar_mes.html', {
                'turnos_pendientes': turnos_pendientes,
                'error': 'No fue posible conectarse con la billetera virtual. Intente nuevamente más tarde.',
            })

        abono.preference_id = preference["id"]
        abono.save()
        return redirect(preference["init_point"])

    return render(request, 'turno/abonar_mes.html', {'turnos_pendientes': turnos_pendientes})

@login_required
def hacerse_abonado(request):
    """Un cliente sin turnos fijos convierte reservas pendientes en turnos fijos y paga con MercadoPago (1-10 del mes)."""
    hoy = timezone.localdate()

    if not (1 <= hoy.day <= 30):
        messages.error(request, "Solo podés hacerte abonado del 1 al 10 de cada mes.")
        return redirect('user:perfil')

    usuario = request.user

    if TurnoFijo.objects.filter(usuario=usuario, activo=True).exists():
        messages.info(request, "Ya sos abonado. Usá 'Abonar Mes' para pagar el mes.")
        return redirect('abonar_mes')

    if Abono.objects.filter(usuario=usuario, mes=hoy.month, anio=hoy.year, estado_pago='aprobado').exists():
        messages.info(request, "Ya pagaste el abono de este mes.")
        return redirect('user:perfil')

    reservas_pendientes = Reserva.objects.filter(
        usuario=usuario,
        estado='pendiente_pago',
        clase__fecha__gte=hoy,
    ).select_related('clase', 'clase__actividad').order_by('clase__fecha', 'clase__hora_inicio')

    if request.method == 'POST':
        reserva_ids = request.POST.getlist('reservas')
        ctx = {'reservas_pendientes': reservas_pendientes}

        if not reserva_ids:
            ctx['error'] = 'Seleccioná al menos una reserva para hacerte abonado.'
            return render(request, 'turno/hacerse_abonado.html', ctx)

        reservas_sel = list(Reserva.objects.filter(
            id__in=reserva_ids,
            usuario=usuario,
            estado='pendiente_pago',
        ).select_related('clase', 'clase__actividad'))

        # Validación backend: no dos reservas con mismo (dia_semana, hora_inicio)
        vistos = set()
        for r in reservas_sel:
            clave = (r.clase.fecha.weekday(), r.clase.hora_inicio)
            if clave in vistos:
                ctx['error'] = (
                    'Seleccionaste dos reservas del mismo día de la semana y horario. '
                    'Solo podés elegir un turno por combinación día/horario.'
                )
                return render(request, 'turno/hacerse_abonado.html', ctx)
            vistos.add(clave)

        # Validación: no abonar clases que ya pasaron
        for r in reservas_sel:
            if r.clase.ya_paso:
                ctx['error'] = f'La clase de {r.clase.actividad.nombre} del {r.clase.fecha.strftime("%d/%m")} ya ha pasado y no puede ser abonada.'
                return render(request, 'turno/hacerse_abonado.html', ctx)

        # Crear Abono en estado pendiente guardando los IDs seleccionados
        # (el webhook creará los TurnoFijos y las Reservas al confirmar el pago)
        abono_existente = Abono.objects.filter(
            usuario=usuario,
            mes=hoy.month,
            anio=hoy.year,
        ).first()

        if abono_existente and abono_existente.estado_pago == 'aprobado':
            messages.info(request, "Ya pagaste el abono de este mes.")
            return redirect('user:perfil')

        if abono_existente:
            abono = abono_existente
            abono.reservas_origen_ids = ','.join(str(r.id) for r in reservas_sel)
            abono.estado_pago = 'pendiente'
            abono.save()
        else:
            abono = Abono.objects.create(
                usuario=usuario,
                mes=hoy.month,
                anio=hoy.year,
                cantidad_turnos_fijos=len(reservas_sel),
                descuento_porcentaje=0,
                monto_total=Decimal('0'),
                monto_final=Decimal('0'),
                metodo_pago='mercado_pago',
                estado_pago='pendiente',
                reservas_origen_ids=','.join(str(r.id) for r in reservas_sel),
        )

        # Calcular precio estimado para mostrárselo a MP (el definitivo lo calcula el webhook)
        # Para esto creamos TurnoFijo temporales en memoria sin guardarlos
        from decimal import Decimal as D
        n = len(reservas_sel)
        descuento = 20 if n >= 3 else (10 if n == 2 else 0)
        precio_estimado = sum(r.clase.actividad.precio for r in reservas_sel)
        precio_final_estimado = (precio_estimado * D(str(1 - descuento / 100))).quantize(D('0.01'))

        sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
        preference_data = {
            "items": [{
                "title": f"Abono mensual {hoy.month}/{hoy.year} - SIRCA",
                "quantity": 1,
                "currency_id": "ARS",
                "unit_price": float(precio_final_estimado),
            }],
            "external_reference": f"abono_{abono.id}",
            "back_urls": {
                "success": f"{settings.NGROK_URL}/turno/abono/exito/",
                "failure": f"{settings.NGROK_URL}/turno/abono/fallo/",
                "pending": f"{settings.NGROK_URL}/turno/abono/pendiente/",
            },
            "auto_return": "approved",
            "notification_url": f"{settings.NGROK_URL}/pago/webhook/",
        }

        preference_response = sdk.preference().create(preference_data)
        preference = preference_response.get("response", {})
        if "id" not in preference:
            return render(request, 'turno/hacerse_abonado.html', {
                'reservas_pendientes': reservas_pendientes,
                'error': 'No fue posible conectarse con la billetera virtual. Intente nuevamente más tarde',
            })

        abono.preference_id = preference["id"]
        abono.save()

        return redirect(preference["init_point"])

    return render(request, 'turno/hacerse_abonado.html', {
        'reservas_pendientes': reservas_pendientes,
    })

@login_required
def abono_exito(request):
    messages.success(request, "¡Pago del abono exitoso! Tus reservas del mes fueron generadas.")
    return redirect('reservas')


@login_required
def abono_fallo(request):
    messages.error(request, "Pago rechazado")
    return redirect('user:perfil')


@login_required
def abono_pendiente(request):
    messages.warning(request, "Tu pago está pendiente de confirmación.")
    return redirect('user:perfil')

@login_required
def abonar_nuevo_turno_fijo(request):
    """Cualquier cliente convierte reservas pendientes en nuevos TF y paga con MercadoPago (1-10)."""
    hoy = timezone.localdate()

    if not (1 <= hoy.day <= 30):
        messages.error(request, "Solo podés abonar un nuevo turno fijo del 1 al 10 de cada mes.")
        return redirect('user:perfil')

    usuario = request.user

    abono_aprobado = Abono.objects.filter(
        usuario=usuario, mes=hoy.month, anio=hoy.year, estado_pago='aprobado',
    ).exists()
    if abono_aprobado:
        messages.error(
            request,
            "Ya tenés un abono aprobado este mes. Podés agregar nuevos turnos fijos el próximo mes."
        )
        return redirect('user:perfil')

    reservas_pendientes = _reservas_pendientes_sin_superposicion(usuario, hoy)

    if request.method == 'POST':
        reserva_ids = request.POST.getlist('reservas')
        ctx = {'reservas_pendientes': reservas_pendientes}

        if not reserva_ids:
            ctx['error'] = 'Seleccioná al menos una reserva para convertir en turno fijo.'
            return render(request, 'turno/abonar_nuevo_turno_fijo.html', ctx)

        reservas_sel = list(Reserva.objects.filter(
            id__in=reserva_ids, usuario=usuario, estado='pendiente_pago',
        ).select_related('clase', 'clase__actividad'))

        vistos = set()
        for r in reservas_sel:
            clave = (r.clase.fecha.weekday(), r.clase.hora_inicio)
            if clave in vistos:
                ctx['error'] = (
                    'Seleccionaste dos reservas del mismo día y horario. '
                    'Solo podés elegir un turno por combinación día/horario.'
                )
                return render(request, 'turno/abonar_nuevo_turno_fijo.html', ctx)
            vistos.add(clave)

        # Validación: no abonar clases que ya pasaron
        for r in reservas_sel:
            if r.clase.ya_paso:
                ctx['error'] = f'La clase de {r.clase.actividad.nombre} del {r.clase.fecha.strftime("%d/%m")} ya ha pasado y no puede ser abonada.'
                return render(request, 'turno/abonar_nuevo_turno_fijo.html', ctx)

        abono_existente = Abono.objects.filter(usuario=usuario, mes=hoy.month, anio=hoy.year).first()
        if abono_existente and abono_existente.estado_pago == 'aprobado':
            messages.info(request, "Ya pagaste el abono de este mes.")
            return redirect('user:perfil')

        n = len(reservas_sel)
        descuento = 20 if n >= 3 else (10 if n == 2 else 0)
        precio_estimado = sum(r.clase.actividad.precio for r in reservas_sel)
        precio_final_estimado = (precio_estimado * Decimal(str(1 - descuento / 100))).quantize(Decimal('0.01'))

        if abono_existente:
            abono = abono_existente
            abono.reservas_origen_ids = ','.join(str(r.id) for r in reservas_sel)
            abono.estado_pago = 'pendiente'
            abono.save()
        else:
            abono = Abono.objects.create(
                usuario=usuario,
                mes=hoy.month,
                anio=hoy.year,
                cantidad_turnos_fijos=n,
                descuento_porcentaje=0,
                monto_total=Decimal('0'),
                monto_final=Decimal('0'),
                metodo_pago='mercado_pago',
                estado_pago='pendiente',
                reservas_origen_ids=','.join(str(r.id) for r in reservas_sel),
            )

        sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
        preference_data = {
            "items": [{
                "title": f"Nuevo turno fijo {hoy.month}/{hoy.year} - SIRCA",
                "quantity": 1,
                "currency_id": "ARS",
                "unit_price": float(precio_final_estimado),
            }],
            "external_reference": f"abono_{abono.id}",
            "back_urls": {
                "success": f"{settings.NGROK_URL}/turno/abono/exito/",
                "failure": f"{settings.NGROK_URL}/turno/abono/fallo/",
                "pending": f"{settings.NGROK_URL}/turno/abono/pendiente/",
            },
            "auto_return": "approved",
            "notification_url": f"{settings.NGROK_URL}/pago/webhook/",
        }

        preference_response = sdk.preference().create(preference_data)
        preference = preference_response.get("response", {})
        if "id" not in preference:
            return render(request, 'turno/abonar_nuevo_turno_fijo.html', {
                'reservas_pendientes': reservas_pendientes,
                'error': 'No fue posible conectarse con la billetera virtual. Intente nuevamente más tarde.',
            })

        abono.preference_id = preference["id"]
        abono.save()
        return redirect(preference["init_point"])

    return render(request, 'turno/abonar_nuevo_turno_fijo.html', {
        'reservas_pendientes': reservas_pendientes,
    })


@login_required
def ver_turnos_fijos(request):
    """Muestra la lista de TurnoFijo del cliente con estado de pago del mes actual."""
    usuario = request.user
    hoy = timezone.localdate()

    turnos_fijos = TurnoFijo.objects.filter(usuario=usuario, activo=True).select_related('actividad')
    if not turnos_fijos.exists():
        messages.info(request, "No tenés turnos fijos activos.")
        return redirect('reservas')

    abono_mes = Abono.objects.filter(
        usuario=usuario, mes=hoy.month, anio=hoy.year, estado_pago='aprobado',
    ).first()

    ids_abonados = set()
    if abono_mes:
        # Sin campo turnos_fijos_ids: si hay Abono aprobado, todos los TF activos se consideran pagados
        ids_abonados = {tf.id for tf in turnos_fijos}

    DIAS = {0: 'lunes', 1: 'martes', 2: 'miércoles', 3: 'jueves', 4: 'viernes', 5: 'sábado', 6: 'domingo'}
    turnos_con_estado = [
        {
            'turno': tf,
            'dia_nombre': DIAS.get(tf.dia_semana, ''),
            'pagado': tf.id in ids_abonados,
        }
        for tf in turnos_fijos
    ]

    return render(request, 'turno/ver_turnos_fijos.html', {'turnos_con_estado': turnos_con_estado})


@login_required
def registrar_pago_abono_admin(request, user_id):
    """Admin: registra pago de turno fijo para un cliente (renovar o nuevo)."""
    if not es_admin(request.user):
        messages.error(request, "No tenés permisos para registrar pagos.")
        return redirect('core:home')

    from django.contrib.auth import get_user_model as _get_user_model
    Client = _get_user_model()
    client = get_object_or_404(Client, pk=user_id, rol='cliente')
    hoy = timezone.localdate()

    turnos_fijos = TurnoFijo.objects.filter(usuario=client, activo=True).select_related('actividad')
    reservas_disponibles = _reservas_pendientes_sin_superposicion(client, hoy)
    # Sección A: solo TF sin Abono aprobado este mes
    # Sin campo turnos_fijos_ids en el modelo: si hay Abono aprobado → todos ya pagados
    abono_aprobado_mes = Abono.objects.filter(
        usuario=client, mes=hoy.month, anio=hoy.year, estado_pago='aprobado'
    ).first()

    if abono_aprobado_mes:
        turnos_fijos = TurnoFijo.objects.none()
    else:
        turnos_fijos = TurnoFijo.objects.filter(usuario=client, activo=True).select_related('actividad')

    # Sección B: reservas pendientes sin superposición y que no sean ya un TF activo del cliente
    reservas_filtradas = _reservas_pendientes_sin_superposicion(client, hoy)
    tf_existentes = set(
        TurnoFijo.objects.filter(usuario=client, activo=True).values_list('dia_semana', 'hora_inicio')
    )
    reservas_disponibles = [
        r for r in reservas_filtradas
        if (r.clase.fecha.weekday(), r.clase.hora_inicio) not in tf_existentes
    ]

    DIAS = {0: 'lunes', 1: 'martes', 2: 'miércoles', 3: 'jueves', 4: 'viernes', 5: 'sábado', 6: 'domingo'}
    if request.method == 'POST':
        accion = request.POST.get('accion')
        metodo_pago = request.POST.get('metodo_pago', 'efectivo')
        if metodo_pago not in ['efectivo', 'posnet', 'transferencia']:
            metodo_pago = 'efectivo'

        if accion == 'renovar':
            turno_ids = [int(x) for x in request.POST.getlist('turnos_fijos') if x.isdigit()]
            if not turno_ids:
                messages.error(request, 'Seleccioná al menos un turno fijo.')
                return redirect('registrar_pago_abono_admin', user_id=user_id)

            info = _calcular_info_abono_para_turnos(client, turno_ids, hoy.month, hoy.year)
            if not info:
                messages.error(request, 'No hay clases para los turnos seleccionados este mes.')
                return redirect('registrar_pago_abono_admin', user_id=user_id)

            abono_existente = Abono.objects.filter(usuario=client, mes=hoy.month, anio=hoy.year).first()
            if abono_existente and abono_existente.estado_pago == 'aprobado':
                messages.warning(request, 'Este cliente ya tiene el abono de este mes pagado.')
                return redirect('user:client_profile', user_id=user_id)

            if abono_existente:
                abono = abono_existente
                abono.cantidad_turnos_fijos = len(info['turnos_fijos'])
                abono.descuento_porcentaje = info['descuento_porcentaje']
                abono.monto_total = info['monto_total']
                abono.monto_final = info['monto_final']
                abono.metodo_pago = metodo_pago
                abono.estado_pago = 'aprobado'
                abono.save()
            else:
                abono = Abono.objects.create(
                    usuario=client,
                    mes=hoy.month,
                    anio=hoy.year,
                    cantidad_turnos_fijos=len(info['turnos_fijos']),
                    descuento_porcentaje=info['descuento_porcentaje'],
                    monto_total=info['monto_total'],
                    monto_final=info['monto_final'],
                    metodo_pago=metodo_pago,
                    estado_pago='aprobado',
                )

            _crear_reservas_abono(client, abono, info)
            messages.success(request, f'Abono registrado para {client.get_full_name()}.')
            return redirect('user:client_profile', user_id=user_id)

        elif accion == 'nuevo':
            reserva_ids = request.POST.getlist('reservas')
            if not reserva_ids:
                messages.error(request, 'Seleccioná al menos una reserva.')
                return redirect('registrar_pago_abono_admin', user_id=user_id)

            reservas_sel = list(Reserva.objects.filter(
                id__in=reserva_ids, usuario=client, estado='pendiente_pago',
            ).select_related('clase', 'clase__actividad'))

            vistos = set()
            for r in reservas_sel:
                clave = (r.clase.fecha.weekday(), r.clase.hora_inicio)
                if clave in vistos:
                    messages.error(request, 'Hay dos reservas del mismo día y horario.')
                    return redirect('registrar_pago_abono_admin', user_id=user_id)
                vistos.add(clave)

            nuevos_tf_ids = []
            for r in reservas_sel:
                tf, _ = TurnoFijo.objects.get_or_create(
                    usuario=client,
                    dia_semana=r.clase.fecha.weekday(),
                    hora_inicio=r.clase.hora_inicio,
                    defaults={'actividad': r.clase.actividad, 'activo': True},
                )
                nuevos_tf_ids.append(tf.id)

            n = len(nuevos_tf_ids)
            descuento = 20 if n >= 3 else (10 if n == 2 else 0)
            precio_total = sum(r.clase.actividad.precio for r in reservas_sel)
            factor = Decimal(str(1 - descuento / 100))
            precio_final = (precio_total * factor).quantize(Decimal('0.01'))

            abono_existente = Abono.objects.filter(usuario=client, mes=hoy.month, anio=hoy.year).first()
            if abono_existente and abono_existente.estado_pago == 'aprobado':
                messages.warning(request, 'Este cliente ya tiene el abono de este mes pagado.')
                return redirect('user:client_profile', user_id=user_id)

            if abono_existente:
                abono = abono_existente
                abono.reservas_origen_ids = ','.join(str(r.id) for r in reservas_sel)
                abono.cantidad_turnos_fijos = n
                abono.descuento_porcentaje = descuento
                abono.monto_total = precio_total
                abono.monto_final = precio_final
                abono.metodo_pago = metodo_pago
                abono.estado_pago = 'aprobado'
                abono.save()
            else:
                abono = Abono.objects.create(
                    usuario=client,
                    mes=hoy.month,
                    anio=hoy.year,
                    cantidad_turnos_fijos=n,
                    descuento_porcentaje=descuento,
                    monto_total=precio_total,
                    monto_final=precio_final,
                    metodo_pago=metodo_pago,
                    estado_pago='aprobado',
                    reservas_origen_ids=','.join(str(r.id) for r in reservas_sel)
                )

            info = _calcular_info_abono_para_turnos(client, nuevos_tf_ids, hoy.month, hoy.year)
            if info:
                _crear_reservas_abono(client, abono, info)

            messages.success(request, f'Turno fijo registrado para {client.get_full_name()}.')
            return redirect('user:client_profile', user_id=user_id)

    turnos_con_detalle = [
        {'turno': tf, 'dia_nombre': DIAS.get(tf.dia_semana, '')}
        for tf in turnos_fijos
    ]
    return render(request, 'turno/registrar_pago_abono_admin.html', {
        'client': client,
        'turnos_con_detalle': turnos_con_detalle,
        'reservas_disponibles': reservas_disponibles,
        'tiene_turnos_fijos': turnos_fijos.exists(),
        'tiene_reservas': bool(reservas_disponibles),
    })
