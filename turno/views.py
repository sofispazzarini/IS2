
from datetime import datetime, timedelta
from datetime import timedelta
import io
import base64


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

from .models import Clase, Reserva, ListaEspera, Asistencia
from .services import validar_qr
from .forms import ClaseForm
from pago.models import Pago
from actividad.models import Actividad
from user.models import Profesor
from resena.models import Resena
from resena.forms import ResenaForm
from django.db.models import Avg, Count, Sum, Q

from django.urls import reverse

from django.http import HttpResponse

def registrar_asistencia(request, qr_uuid):
    reserva = get_object_or_404(Reserva, qr_uuid=qr_uuid)

    # marcar asistencia
    reserva.estado = "asistida"
    reserva.save()

    return HttpResponse("✔ Asistencia registrada correctamente")


def generar_qr(request, obj_id):
    base_url = "https://supreme-cavalier-unchain.ngrok-free.app"

    url = f"{base_url}/asistencia/{obj_id}/"
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
                    base_url = "https://supreme-cavalier-unchain.ngrok-free.dev"
                    url = f"{base_url}/turno/asistencia/{reserva.qr_uuid}/"
                    qr_image = generar_qr_base64(url)

        reservas_con_info.append({
            'reserva': reserva,
            'puede_cancelar': puede_cancelar,
            'dias_anticipacion': dias_anticipacion,
            'mostrar_qr': mostrar_qr,
            'qr_image': qr_image,
        })

    return render(request, 'turno/mis_turnos.html', {
        'reservas_con_info': reservas_con_info,
        'tiene_turnos': len(reservas_con_info) > 0,
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

    clases = Clase.objects.filter(
        cancelada=False,
        fecha__year=year,
        fecha__month=month,
    ).select_related('actividad', 'profesor')

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
            'salon': clase.salon,
            'precio': float(clase.actividad.precio),
            'es_pasada': es_pasada,
        })

    for fecha in dias:
        dias[fecha].sort(key=lambda x: x['hora_inicio'])

    # Mensaje vacío cuando se filtra sin resultados
    mensaje_vacio = None
    if not dias:
        if horario:
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
                base_url = "https://supreme-cavalier-unchain.ngrok-free.app"
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

    if (clase.fecha - hoy) < timedelta(days=2):
        messages.error(request, "Las cancelaciones con menos de dos días de anticipación no están permitidas.")
        return redirect('reservas')

    if request.method == 'POST':
        era_abonada = reserva.estado == 'confirmada'
        reserva.estado = 'cancelada'
        reserva.save()

        if era_abonada:
            return redirect('opciones_reembolso', reserva_id=reserva.id)
        else:
            messages.success(request, "Reserva cancelada exitosamente.")
            return redirect('reservas')

    return render(request, 'turno/confirmar_cancelacion.html', {'reserva': reserva})


@login_required
def opciones_reembolso(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user, estado='cancelada')
    pago = reserva.pagos.filter(estado_pago='aprobado').first()
    monto = pago.monto if pago else reserva.clase.actividad.precio

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
    salon = request.GET.get('salon', '').strip()

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
    if salon:
        clases = clases.filter(salon__icontains=salon)

    clases = clases.order_by('fecha', 'hora_inicio').select_related('actividad', 'profesor')

    return render(request, 'turno/admin_clases.html', {
        'clases': clases,
        'es_dueno': es_dueno(request.user),
        'actividades': Actividad.objects.filter(activa=True).order_by('nombre'),
        'profesores': Profesor.objects.filter(activo=True).order_by('apellido', 'nombre'),
        'filtro_actividad': actividad_id,
        'filtro_profesor': profesor_id,
        'filtro_estado': estado,
        'filtro_fecha_desde': fecha_desde,
        'filtro_fecha_hasta': fecha_hasta,
        'filtro_salon': salon,
        'hay_filtros': any([actividad_id, profesor_id, estado, fecha_desde, fecha_hasta, salon]),
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
    """Cancelar una clase y notificar a los usuarios inscriptos (solo dueño)."""
    if not es_dueno(request.user):
        messages.error(request, "Solo el dueño puede cancelar clases.")
        return redirect('admin_clases')

    clase = get_object_or_404(Clase, id=clase_id)

    if request.method == 'POST':
        reservas_activas = Reserva.objects.filter(
            clase=clase
        ).exclude(estado='cancelada').select_related('usuario')

        emails_enviados = 0
        for reserva in reservas_activas:
            usuario = reserva.usuario
            if usuario.notificaciones_activas and usuario.email:
                try:
                    send_mail(
                        subject=f"Clase cancelada: {clase.actividad.nombre}",
                        message=f"Hola {usuario.first_name or usuario.username},\n\n"
                                f"La clase fue cancelada.\n\n"
                                f"Detalles de la clase:\n"
                                f"- Actividad: {clase.actividad.nombre}\n"
                                f"- Fecha: {clase.fecha.strftime('%d/%m/%Y')}\n"
                                f"- Horario: {clase.hora_inicio.strftime('%H:%M')} hs\n\n"
                                f"Disculpá las molestias.\n\n"
                                f"Saludos,\nEquipo SIRCA",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[usuario.email],
                        fail_silently=True,
                    )
                    emails_enviados += 1
                except Exception:
                    pass

            reserva.estado = 'cancelada'
            reserva.save()

        clase.cancelada = True
        clase.save()

        messages.success(
            request,
            f"Clase cancelada. Se notificó a {emails_enviados} usuario(s) inscripto(s)."
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

    return render(request, 'turno/detalle_clase.html', {
        'clase': clase,
        'reservas_activas': reservas_activas,
        'reservas_canceladas': reservas_canceladas,
        'asistencias': asistencias,
        'pagos': pagos,
        'resenas': resenas,
        'promedio_resenas': promedio_resenas,
        'stats': stats,
        'cupos_disponibles': cupos_disponibles,
        'total_recaudado': total_recaudado,
        'clase_finalizada': clase_finalizada,
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
            messages.success(request, '¡Gracias por tu reseña!')
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
        'form': form,
    })


def generar_qr_base64(data):
    """Genera un código QR como imagen base64."""
    print("QR URL:", data)
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
    """API para validar un código QR y registrar asistencia."""
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
