from django import forms
from django.contrib.auth import get_user_model
from datetime import date
import re

from .models import Profesor

User = get_user_model()


class ProfesorForm(forms.ModelForm):
    class Meta:
        model = Profesor
        fields = ['nombre', 'apellido', 'telefono', 'email', 'especialidad', 'descripcion', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input'}),
            'apellido': forms.TextInput(attrs={'class': 'form-input'}),
            'telefono': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'especialidad': forms.TextInput(attrs={'class': 'form-input'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class EditarPerfilForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "telefono"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre"}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Apellido"}),
            "telefono": forms.TextInput(attrs={"class": "form-control", "placeholder": "Teléfono"}),
        }
        labels = {
            "first_name": "Nombre",
            "last_name": "Apellido",
            "telefono": "Teléfono",
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_first_name(self):
        first_name = self.cleaned_data.get("first_name")
        if not first_name or not first_name.strip():
            raise forms.ValidationError("El campo nombre es obligatorio")
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$', first_name):
            raise forms.ValidationError("El nombre contiene caracteres inválidos")
        return first_name.strip()

    def clean_last_name(self):
        last_name = self.cleaned_data.get("last_name")
        if not last_name or not last_name.strip():
            raise forms.ValidationError("El campo apellido es obligatorio")
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$', last_name):
            raise forms.ValidationError("El apellido contiene caracteres inválidos")
        return last_name.strip()

    def clean_telefono(self):
        telefono = self.cleaned_data.get("telefono")
        if telefono:
            if not re.match(r'^\d+$', telefono):
                raise forms.ValidationError("El teléfono solo puede contener números")
            if self.user:
                if User.objects.filter(telefono=telefono).exclude(pk=self.user.pk).exists():
                    raise forms.ValidationError("Este teléfono ya está registrado por otro usuario")
        return telefono


class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Correo Electrónico",
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Correo electrónico"}),
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Contraseña"}),
    )


class ChangePasswordForm(forms.Form):
    password = forms.CharField(
        label="Contraseña",
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Contraseña"}),
    )
    password_confirm = forms.CharField(
        label="Confirmar Contraseña",
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirmar Contraseña"}),
    )

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            if len(password) < 8 or len(password) > 20:
                raise forms.ValidationError("La contraseña debe tener entre 8 y 20 caracteres")
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if not password or not password_confirm:
            raise forms.ValidationError("Completar contraseña")

        if password != password_confirm:
            raise forms.ValidationError("Las contraseñas no coinciden")

        return cleaned_data


class RegistroForm(forms.ModelForm):
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    password_confirm = forms.CharField(
        label="Confirmar Contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    fecha_nacimiento = forms.DateField(
        label="Fecha de Nacimiento",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        input_formats=["%Y-%m-%d", "%d/%m/%Y"],
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "dni", "telefono", "fecha_nacimiento"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre"}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Apellido"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Correo electrónico"}),
            "dni": forms.TextInput(attrs={"class": "form-control", "placeholder": "DNI"}),
            "telefono": forms.TextInput(attrs={"class": "form-control", "placeholder": "Teléfono"}),
        }
        labels = {
            "first_name": "Nombre",
            "last_name": "Apellido",
            "email": "Correo Electrónico",
            "dni": "DNI",
            "telefono": "Teléfono",
        }

    def clean_fecha_nacimiento(self):
        fecha_nacimiento = self.cleaned_data.get("fecha_nacimiento")
        if fecha_nacimiento:
            hoy = date.today()
            edad = (
                hoy.year
                - fecha_nacimiento.year
                - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
            )
            if edad < 15:
                raise forms.ValidationError("Tenes que tener al menos 15 años de edad, vuelva a intentarlo")
        return fecha_nacimiento

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo ya está asociado a una cuenta, vuelva a intentarlo")
        return email

    def clean_dni(self):
        dni = self.cleaned_data.get("dni")
        if dni and User.objects.filter(dni=dni).exists():
            raise forms.ValidationError("DNI ya asociado a una cuenta, vuelva a intentarlo")
        return dni

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            if len(password) < 8 or len(password) > 20:
                raise forms.ValidationError(
                    "Tu contraseña debe tener entre 8 y 20 caracteres, vuelva a intentarlo."
                )
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm:
            if password != password_confirm:
                raise forms.ValidationError("Las contraseñas no coinciden, vuelva a intentarlo")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        user.set_password(password)
        user.username = self.cleaned_data.get("email")
        if commit:
            user.save()
        return user
