from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponseForbidden
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils.crypto import get_random_string
from .forms import RegistroForm, LoginForm, ChangePasswordForm, EditarPerfilForm, EditarClienteForm, ProfesorForm
from .models import HistorialUsuarioBaja, Profesor
from django.utils.http import urlsafe_base64_encode
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.views.decorators.cache import never_cache
from .forms import RestablecerContrasenaForm
from django.utils import timezone

@never_cache
def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "Inicio de sesión exitoso")
                if user.rol in ('secretario', 'dueno'):
                    return redirect('user:client_list')
                return redirect('core:home')
            else:
                messages.error(request, "El mail o la contraseña son incorrectos")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, str(error))
    else:
        form = LoginForm()

    return render(request, 'user/login.html', {'form': form})

@never_cache
def registro(request):
    if request.user.is_authenticated:
        return redirect('core:home')
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Cuenta creada exitosamente")
            return redirect("user:login")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, str(error))
    else:
        form = RegistroForm()

    return render(request, "user/registro.html", {"form": form})


def _es_admin(request):
    if not request.user.is_authenticated:
        return False
    rol = getattr(request.user, 'rol', None)
    return rol in ('secretario', 'dueno')


@login_required(login_url='user:login')
def client_list(request):
    if not _es_admin(request):
        return HttpResponseForbidden("Acceso denegado")

    busqueda = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '')

    users = get_user_model().objects.filter(rol='cliente')

    if estado == 'activos':
        users = users.filter(activo=True)
    elif estado == 'inactivos':
        users = users.filter(activo=False)
    if busqueda:
        users = users.filter(
            Q(email__icontains=busqueda) |
            Q(dni__icontains=busqueda) |
            Q(first_name__icontains=busqueda) |
            Q(last_name__icontains=busqueda)
        )

    users = users.order_by('first_name', 'last_name')

    return render(request, 'user/client_list.html', {
        'clients': users,
        'filtro_busqueda': busqueda,
        'filtro_estado': estado,
        'hay_filtros': any([busqueda, estado]),
    })


@login_required(login_url='user:login')
def client_profile(request, user_id):
    if not _es_admin(request):
        return HttpResponseForbidden("Acceso denegado")

    client = get_object_or_404(get_user_model(), pk=user_id, rol='cliente')
    return render(request, 'user/client_profile.html', {'client': client})

@login_required(login_url='user:login')
def historial_asistencias(request, user_id):
    if not _es_admin(request):
        return HttpResponseForbidden("Acceso denegado")
    from turno.models import Reserva
    client = get_object_or_404(get_user_model(), pk=user_id, rol='cliente')
    asistencias = Reserva.objects.filter(usuario=client, estado='asistida').select_related('clase', 'clase__actividad', 'clase__profesor').order_by('-clase__fecha', '-clase__hora_inicio')
    return render(request, 'user\\historial_asistencias.html', {
        'client': client,
        'asistencias': asistencias,
    })

@login_required(login_url='user:login')
def editar_cliente(request, user_id):
    if not _es_admin(request):
        return HttpResponseForbidden("Acceso denegado")

    client = get_object_or_404(get_user_model(), pk=user_id, rol='cliente')

    if request.method == 'POST':
        form = EditarClienteForm(request.POST, instance=client, client=client)
        if form.is_valid():
            form.save()
            messages.success(request, 'Datos del cliente actualizados correctamente.')
            return redirect('user:client_profile', user_id=client.pk)
    else:
        form = EditarClienteForm(instance=client, client=client)

    return render(request, 'user/editar_cliente.html', {'form': form, 'client': client})


@login_required(login_url='user:login')
def secretary_reset_password(request, user_id):
    if not _es_admin(request):
        return HttpResponseForbidden("Acceso denegado")

    client = get_object_or_404(get_user_model(), pk=user_id, rol='cliente')

    if request.method != 'POST':
        return redirect('user:client_profile', user_id=client.pk)

    temp_password = get_random_string(length=12)
    client.set_password(temp_password)
    client.save()

    subject = 'Contraseña temporal SIRCA'
    message = render_to_string('email/secretary_temp_password_email.txt', {
        'client': client,
        'temp_password': temp_password,
    })
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [client.email],
        fail_silently=False,
    )

    messages.success(request, 'Contraseña temporal enviada al correo del cliente.')
    return redirect('user:client_profile', user_id=client.pk)


@login_required(login_url='user:login')
def dar_baja_cliente(request, user_id):
    if not _es_admin(request):
        return HttpResponseForbidden("Acceso denegado")

    User = get_user_model()
    client = get_object_or_404(User, pk=user_id, rol='cliente')

    if request.method == 'POST':
        HistorialUsuarioBaja.objects.create(
            nombre=client.first_name,
            apellido=client.last_name,
            email=client.email,
            dni=client.dni,
            telefono=client.telefono,
            fecha_nacimiento=client.fecha_nacimiento,
            fecha_registro_original=client.fecha_registro,
            creditos_al_momento=client.creditos,
            dado_baja_por=request.user,
            motivo=request.POST.get('motivo', ''),
        )

        email_cliente = client.email
        client.delete()

        messages.success(request, f'Usuario {email_cliente} eliminado exitosamente. Los datos fueron guardados en el historial.')
        return redirect('user:client_list')

    return render(request, 'user/confirmar_baja.html', {'client': client})


@login_required(login_url='user:login')
def buscar_cliente(request):
    if not _es_admin(request):
        return HttpResponseForbidden("Acceso denegado")

    email = request.GET.get('email', '').strip()

    if not email:
        messages.error(request, 'Ingrese un email para buscar')
        return redirect('user:client_list')

    User = get_user_model()
    try:
        client = User.objects.get(email=email, rol='cliente')
        return redirect('user:client_profile', user_id=client.pk)
    except User.DoesNotExist:
        messages.error(request, 'No se ha encontrado el usuario')
        return redirect('user:client_list')


@login_required(login_url='user:login')
def change_password(request):
    if request.method == "POST":
        form = ChangePasswordForm(request.POST, user=request.user)
        if form.is_valid():
            password = form.cleaned_data.get("password")
            user = request.user
            user.set_password(password)
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Cambio de contraseña exitoso")
            return redirect('core:home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, str(error))
    else:
        form = ChangePasswordForm()

    return render(request, 'user/change_password.html', {'form': form})


@login_required(login_url='user:login')
def perfil_view(request):
    user = request.user
    perfil_form = EditarPerfilForm(instance=user, user=user)
    password_form = ChangePasswordForm()

    if request.method == "POST":
        if 'guardar_perfil' in request.POST:
            perfil_form = EditarPerfilForm(request.POST, instance=user, user=user)
            if perfil_form.is_valid():
                cambios = []
                if 'first_name' in perfil_form.changed_data or 'last_name' in perfil_form.changed_data:
                    cambios.append('datos')
                if 'telefono' in perfil_form.changed_data:
                    cambios.append('telefono')

                perfil_form.save()

                if 'telefono' in cambios and len(cambios) == 1:
                    messages.success(request, "Teléfono actualizado exitosamente")
                elif cambios:
                    messages.success(request, "Datos actualizados exitosamente")
                return redirect('user:perfil')
            else:
                tiene_error_nombre_vacio = 'first_name' in perfil_form.errors and any(
                    'obligatorio' in str(e).lower() for e in perfil_form.errors['first_name']
                )
                tiene_error_apellido_vacio = 'last_name' in perfil_form.errors and any(
                    'obligatorio' in str(e).lower() for e in perfil_form.errors['last_name']
                )

                if tiene_error_nombre_vacio or tiene_error_apellido_vacio:
                    messages.error(request, "El campo nombre y el campo apellido son obligatorios")
                    for field, errors in perfil_form.errors.items():
                        for error in errors:
                            if 'obligatorio' not in str(error).lower():
                                messages.error(request, str(error))
                else:
                    for field, errors in perfil_form.errors.items():
                        for error in errors:
                            messages.error(request, str(error))

        elif 'cambiar_password' in request.POST:
            password_form = ChangePasswordForm(request.POST, user=request.user)
            if password_form.is_valid():
                password = password_form.cleaned_data.get("password")
                user.set_password(password)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Cambio de contraseña exitoso")
                return redirect('user:perfil')
            else:
                for field, errors in password_form.errors.items():
                    for error in errors:
                        messages.error(request, str(error))

    from turno.models import TurnoFijo, Abono
    hoy = timezone.localdate()
    es_ventana_pago = 1 <= hoy.day <= 20
    tiene_turnos_fijos = False
    abono_pagado_mes = False
    if user.rol == 'cliente':
        tiene_turnos_fijos = TurnoFijo.objects.filter(usuario=user, activo=True).exists()
        abono_pagado_mes = Abono.objects.filter(
            usuario=user,
            mes=hoy.month,
            anio=hoy.year,
            estado_pago='aprobado',
        ).exists()

    return render(request, 'user/perfil.html', {
        'perfil_form': perfil_form,
        'password_form': password_form,
        'es_ventana_pago': es_ventana_pago,
        'tiene_turnos_fijos': tiene_turnos_fijos,
        'abono_pagado_mes': abono_pagado_mes,
    })


def logout_view(request):
    logout(request)
    messages.success(request, "Sesión cerrada exitosamente")
    return redirect('user:login')


def _es_dueno(request):
    if not request.user.is_authenticated:
        return False
    return getattr(request.user, 'rol', None) == 'dueno'


@login_required(login_url='user:login')
def admin_profesores(request):
    """Panel de administración de profesores."""
    if not _es_admin(request):
        return HttpResponseForbidden("Acceso denegado")

    activo = request.GET.get('activo', '')
    especialidad = request.GET.get('especialidad', '')
    busqueda = request.GET.get('q', '').strip()

    profesores = Profesor.objects.all()

    if activo == 'activos':
        profesores = profesores.filter(activo=True)
    elif activo == 'inactivos':
        profesores = profesores.filter(activo=False)
        
    if especialidad:
        profesores = profesores.filter(especialidad=especialidad)
        
    if busqueda:
        # 🛡️ Agregamos el filtro por DNI manteniendo el nombre, apellido y email originales
        profesores = profesores.filter(
            Q(nombre__icontains=busqueda) |
            Q(apellido__icontains=busqueda) |
            Q(email__icontains=busqueda) |
            Q(dni__icontains=busqueda)
        )

    profesores = profesores.order_by('apellido', 'nombre')
    especialidades = Profesor.objects.values_list('especialidad', flat=True).distinct().order_by('especialidad')

    return render(request, 'user/admin_profesores.html', {
        'profesores': profesores,
        'es_dueno': _es_dueno(request),
        'especialidades': especialidades,
        'filtro_activo': activo,
        'filtro_especialidad': especialidad,
        'filtro_busqueda': busqueda,
        'hay_filtros': any([activo, especialidad, busqueda]),
    })


@login_required(login_url='user:login')
def crear_profesor(request):
    """Crear un nuevo profesor."""
    if not _es_admin(request):
        return HttpResponseForbidden("Acceso denegado")

    if request.method == 'POST':
        form = ProfesorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Profesor creado con éxito.")
            return redirect('user:admin_profesores')
    else:
        form = ProfesorForm()

    return render(request, 'user/crear_profesor.html', {'form': form})


@login_required(login_url='user:login')
def modificar_profesor(request, profesor_id):
    """Modificar un profesor existente."""
    if not _es_dueno(request):
        messages.error(request, "Solo el dueño puede modificar profesores.")
        return redirect('user:admin_profesores')

    profesor = get_object_or_404(Profesor, id=profesor_id)

    if request.method == 'POST':
        form = ProfesorForm(request.POST, instance=profesor)
        if form.is_valid():
            # 🟢 VALIDACIÓN DE CAMBIOS: Si los campos están iguales al estado original
            if not form.has_changed():
                messages.info(request, "No se registraron cambios en los datos del profesor.")
                return redirect('user:admin_profesores')

            form.save()
            messages.success(request, "Profesor modificado con éxito.")
            return redirect('user:admin_profesores')
    else:
        form = ProfesorForm(instance=profesor)

    return render(request, 'user/modificar_profesor.html', {
        'form': form,
        'profesor': profesor,
    })


@login_required(login_url='user:login')
def eliminar_profesor(request, profesor_id):
    """Eliminar un profesor (solo si no tiene clases activas)."""
    if not _es_dueno(request):
        messages.error(request, "Solo el dueño puede eliminar profesores.")
        return redirect('user:admin_profesores')

    profesor = get_object_or_404(Profesor, id=profesor_id)

    # Filtramos para ver si tiene clases que NO estén canceladas
    tiene_clases_activas = profesor.clases.filter(cancelada=False).exists()

    if request.method == 'POST':
        if tiene_clases_activas:
            messages.error(request, "No se puede eliminar el profesor porque tiene clases activas vigentes.")
            return redirect('user:admin_profesores')

        profesor.delete()
        messages.success(request, "Profesor eliminado con éxito.")
        return redirect('user:admin_profesores')

    return render(request, 'user/confirmar_eliminar_profesor.html', {
        'profesor': profesor,
        'tiene_clases': tiene_clases_activas,
    })



def recuperar_contrasena_view(request):
    User = get_user_model()
    
    if request.method == "POST":
        email_ingresado = request.POST.get("email", "").strip()

        if not email_ingresado:
            messages.error(request, "Ingrese un correo electrónico para la recuperación.")
            return render(request, 'recuperar_contrasena.html')
        
        usuarios = User.objects.filter(email=email_ingresado)

        if usuarios.exists():
            user = usuarios.first()
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            
            link_recuperacion = f"http://127.0.0.1:8000/reset/{uidb64}/{token}/"
            
            asunto = "Restablecer Contraseña - SIRCA"
            mensaje_texto = (
                f"Hola {user.username if hasattr(user, 'username') else 'Usuario'},\n\n"
                f"Solicitaste restablecer tu contraseña en SIRCA. "
                f"Ingresá al siguiente enlace para ingresar tu nueva clave:\n\n"
                f"{link_recuperacion}\n\n"
                f"Si no solicitaste este cambio, podés ignorar este correo de forma segura."
            )
            
            send_mail(
                subject=asunto,
                message=mensaje_texto,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email_ingresado], 
                fail_silently=False,
            )
            
            # ESCENARIO I: El mail existe, mandamos el correo pero informamos de forma genérica
            messages.success(request, "En caso de haber ingresado una dirección registrada, se enviará un email para recuperar la contraseña")
        else:
            # ESCENARIO II: El mail NO existe, NO mandamos nada pero informamos EXACTAMENTE LO MISMO
            messages.success(request, "En caso de haber ingresado una dirección registrada, se enviará un email para recuperar la contraseña")

        return render(request, 'recuperar_contrasena.html')

    return render(request, 'recuperar_contrasena.html')



def confirmar_restablecimiento_view(request, uidb64, token):
    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        validlink = True
        
        if request.method == "POST":
            form = RestablecerContrasenaForm(request.POST)
            
            if form.is_valid():
                nueva_clave = form.cleaned_data.get("new_password1")
                user.set_password(nueva_clave)
                user.save()
                
                messages.success(request, "¡Contraseña restablecida con éxito! Ya podés iniciar sesión.")
                return redirect('user:login') 
            else:
                # 🟢 CORRECCIÓN: NO usamos messages.error() aquí.
                # Al dejar que actúe form.errors, el error se renderiza únicamente
                # abajo de los inputs correspondientes a través del contexto HTML.
                pass
        else:
            form = RestablecerContrasenaForm()
    else:
        validlink = False
        form = None

    return render(request, 'password_reset_confirm.html', {
        'validlink': validlink,
        'uid': uidb64,
        'token': token,
        'form': form
    })