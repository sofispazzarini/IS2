from datetime import timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings

from .models import Clase, Reserva, ListaEspera, Asistencia
from .forms import ClaseForm
from pago.models import Pago
from resena.models import Resena
from resena.forms import ResenaForm
from django.db.models import Avg, Count, Sum, Q


def es_admin(user):
    return user.rol in ('secretario', 'dueno')


def es_dueno(user):
    return user.rol == 'dueno'


@login_required
def mis_turnos(request):
    """Muestra los turnos/reservas próximas del usuario."""
    hoy = timezone.now().date()

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
        reservas_con_info.append({
            'reserva': reserva,
            'puede_cancelar': puede_cancelar,
            'dias_anticipacion': dias_anticipacion,
        })

    return render(request, 'turno/mis_turnos.html', {
        'reservas_con_info': reservas_con_info,
        'tiene_turnos': len(reservas_con_info) > 0,
    })

@login_required
def lista_clases(request):
    """Muestra todas las clases disponibles que no han sido canceladas."""
    clases = Clase.objects.filter(
        cancelada=False,
        fecha__gte=timezone.now().date()
    ).order_by('fecha', 'hora_inicio')
    return render(request, 'turno/lista_clases.html', {'clases': clases})

@login_required
def pedir_turno(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id)
    usuario = request.user

    if request.method == 'POST':
        # 1. Escenario III: Superposición de turnos
        superposicion = Reserva.objects.filter(
            usuario=usuario,
            clase__fecha=clase.fecha,
            clase__hora_inicio=clase.hora_inicio,
        ).exclude(estado='cancelada').exists()

        if superposicion:
            # En lugar de explotar, mandamos el error al mismo template
            return render(request, 'turno/pedir_turno.html', {
                'clase': clase,
                'error': 'Error por superposición de turnos.'
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
    return render(request, 'turno/reserva_exitosa.html', {'reserva': reserva})


@login_required
def cancelar_reserva(request, reserva_id):
    # Buscamos la reserva del usuario actual
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)
    clase = reserva.clase
    hoy = timezone.now().date()

    # REGLA DE NEGOCIO: Mínimo 2 días de anticipación
    # Si la clase es el 16 y hoy es 14, la diferencia es 2 (Permitido)
    # Si la clase es el 15 y hoy es 14, la diferencia es 1 (No permitido)
    if (clase.fecha - hoy) < timedelta(days=2):
        # Escenario III: Cancelación fallida
        messages.error(request, "Las cancelaciones con menos de dos días de anticipación no están permitidas.")
        return redirect('reservas')

    if request.method == 'POST':
        estado_anterior = reserva.estado
        reserva.estado = 'cancelada'
        reserva.save()

        if estado_anterior == 'pendiente_pago':
            messages.success(request, "La cancelación fue exitosa. Se aumentó la disponibilidad de cupos.")
        else:
            messages.success(request, "La cancelación fue exitosa. ¿Deseas la devolución del dinero o acumulación de créditos?")

        return redirect('reservas')

    return render(request, 'turno/confirmar_cancelacion.html', {'reserva': reserva})


@login_required
def admin_clases(request):
    """Panel de administración de clases para secretarios y dueños."""
    if not es_admin(request.user):
        messages.error(request, "No tienes permisos para acceder a esta sección.")
        return redirect('core:home')

    clases = Clase.objects.filter(
        fecha__gte=timezone.now().date()
    ).order_by('fecha', 'hora_inicio').select_related('actividad', 'profesor')

    return render(request, 'turno/admin_clases.html', {
        'clases': clases,
        'es_dueno': es_dueno(request.user),
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

    reservas = Reserva.objects.filter(clase=clase).select_related('usuario').order_by('-fecha_reserva')

    pagos = Pago.objects.filter(reserva__clase=clase).select_related('reserva__usuario').order_by('-fecha_pago')

    resenas = Resena.objects.filter(actividad=clase.actividad).select_related('usuario').order_by('-fecha')[:5]

    promedio_resenas = Resena.objects.filter(actividad=clase.actividad).aggregate(promedio=Avg('puntuacion'))['promedio']

    stats = reservas.aggregate(
        total=Count('id'),
        confirmadas=Count('id', filter=Q(estado='confirmada')),
        pendientes=Count('id', filter=Q(estado='pendiente_pago')),
        canceladas=Count('id', filter=Q(estado='cancelada')),
        asistidas=Count('id', filter=Q(estado='asistida')),
    )

    cupos_disponibles = clase.cupo_maximo - (stats['confirmadas'] + stats['pendientes'])

    total_recaudado = pagos.filter(estado_pago='aprobado').aggregate(total=Sum('monto'))['total'] or 0

    return render(request, 'turno/detalle_clase.html', {
        'clase': clase,
        'reservas': reservas,
        'pagos': pagos,
        'resenas': resenas,
        'promedio_resenas': promedio_resenas,
        'stats': stats,
        'cupos_disponibles': cupos_disponibles,
        'total_recaudado': total_recaudado,
        'es_dueno': es_dueno(request.user),
    })


@login_required
def ver_clase(request, clase_id):
    """Vista pública de detalle de clase para usuarios normales."""
    clase = get_object_or_404(
        Clase.objects.select_related('actividad', 'profesor'),
        id=clase_id
    )

    resenas = Resena.objects.filter(
        actividad=clase.actividad
    ).select_related('usuario').order_by('-fecha')

    promedio_resenas = resenas.aggregate(promedio=Avg('puntuacion'))['promedio']
    total_resenas = resenas.count()

    reservas_activas = Reserva.objects.filter(clase=clase).exclude(estado='cancelada').count()
    cupos_disponibles = clase.cupo_maximo - reservas_activas

    usuario_tiene_reserva = Reserva.objects.filter(
        usuario=request.user,
        clase=clase
    ).exclude(estado='cancelada').exists()

    usuario_asistio = Reserva.objects.filter(
        usuario=request.user,
        clase__actividad=clase.actividad,
        estado='asistida'
    ).exists()

    resena_usuario = Resena.objects.filter(
        usuario=request.user,
        actividad=clase.actividad
    ).first()

    form = ResenaForm()

    if request.method == 'POST' and 'crear_resena' in request.POST:
        form = ResenaForm(request.POST)
        if form.is_valid():
            resena = form.save(commit=False)
            resena.usuario = request.user
            resena.actividad = clase.actividad
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
        'resena_usuario': resena_usuario,
        'form': form,
    })
