from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from .forms import RegistroForm, LoginForm, ChangePasswordForm


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

