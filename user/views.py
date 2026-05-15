from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponseForbidden
from django.template.loader import render_to_string
from django.utils.crypto import get_random_string
from .forms import RegistroForm, LoginForm, ChangePasswordForm
from django.contrib.auth.forms import PasswordResetForm
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.hashers import check_password


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "Inicio de sesión exitoso")
                return redirect('core:home')
            else:
                # Verificar si el usuario existe
                try:
                    User = get_user_model()
                    user_exists = User.objects.filter(email=email).exists()
                    if user_exists:
                        messages.error(request, "La contraseña ingresada es inválida")
                    else:
                        messages.error(request, "El correo ingresado no se encuentra registrado")
                except:
                    messages.error(request, "Error en el inicio de sesión")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, str(error))
    else:
        form = LoginForm()

    return render(request, 'user/login.html', {'form': form})


def registro(request):
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Cuenta creada exitosamente")
            return redirect("user:registro")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, str(error))
    else:
        form = RegistroForm()

    return render(request, "user/registro.html", {"form": form})


def _secretario_necesario(request):
    if not request.user.is_authenticated:
        return False
    return getattr(request.user, 'rol', None) == 'secretario'


@login_required(login_url='user:login')
def client_list(request):
    if not _secretario_necesario(request):
        return HttpResponseForbidden("Acceso denegado")

    users = get_user_model().objects.filter(rol='cliente').order_by('first_name', 'last_name')
    return render(request, 'user/client_list.html', {'clients': users})


@login_required(login_url='user:login')
def client_profile(request, user_id):
    if not _secretario_necesario(request):
        return HttpResponseForbidden("Acceso denegado")

    client = get_object_or_404(get_user_model(), pk=user_id, rol='cliente')
    return render(request, 'user/client_profile.html', {'client': client})


@login_required(login_url='user:login')
def secretary_reset_password(request, user_id):
    if not _secretario_necesario(request):
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
def change_password(request):
    if request.method == "POST":
        form = ChangePasswordForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data.get("password")
            user = request.user
            user.set_password(password)
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Contraseña actualizada exitosamente")
            return redirect('core:home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, str(error))
    else:
        form = ChangePasswordForm()

    return render(request, 'user/change_password.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, "Sesión cerrada exitosamente")
    return redirect('user:login')

# RECUPERAR CONTRASENA
def recuperar_contrasena_view(request):
    # Obtenemos dinámicamente el modelo de usuario personalizado del equipo ('user.User')
    User = get_user_model()
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        # ESCENARIO III: Envío de mail fallido por mail no ingresado
        if not email:
            messages.error(request, "Ingrese un correo electrónico para la recuperación.")
            return render(request, 'recuperar_contrasena.html')
            
        # ESCENARIO II: Envío de mail fallido por mail no registrado
        # Ahora sí va a buscar en la tabla correcta ('user_user') donde saltó el error hoy temprano
        if not User.objects.filter(email=email).exists():
            messages.error(request, "El mail ingresado no se encuentra registrado.")
            return render(request, 'recuperar_contrasena.html')
            
        # ESCENARIO I: Envío de mail exitoso
        form = PasswordResetForm({'email': email})
        if form.is_valid():
            form.save(
                request=request,
                email_template_name='registration/password_reset_email.html', 
                subject_template_name='registration/password_reset_subject.txt'
            )
            messages.success(request, "El sistema envía un mail de recuperación al correo ingresado.")
            return redirect('/auth/login/')
            
    return render(request, 'recuperar_contrasena.html')

# --- PEGÁ ESTA FUNCIÓN NUEVA ABAJO DE TU MÉTODO ACTUAL ---
def cambiar_contrasena_view(request, uidb64, token):
    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        usuario = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        usuario = None

    if usuario is not None:
        if request.method == 'POST':
            print("DATOS RECIBIDOS EN POST:", request.POST)
            clave1 = request.POST.get('new_password1')
            clave2 = request.POST.get('new_password2')

            if clave1 != clave2:
                messages.error(request, "Las contraseñas no coinciden.")
                return render(request, 'password_reset_confirm.html', {'validlink': True})

            # --- SOLUCIÓN DE COMPATIBILIDAD CON EL LOGIN ---
            # Como el login de tus compañeros busca por username=email,
            # obligamos a que el campo username contenga el email exacto.
            usuario.username = usuario.email  
            
            # Seteamos la contraseña encriptada correctamente
            usuario.set_password(clave1)
            
            # Guardamos los cambios de forma definitiva
            usuario.save()
            # -----------------------------------------------

            print(f"¡Sincronización exitosa! Username: {usuario.username} | Email: {usuario.email}")

            messages.success(request, "¡Tu contraseña ha sido cambiada con éxito!")
            return render(request, 'password_reset_complete.html')

        return render(request, 'password_reset_confirm.html', {'validlink': True})
    else:
        return render(request, 'password_reset_confirm.html', {'validlink': False})