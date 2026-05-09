from django import forms
from django.contrib.auth import get_user_model
from datetime import date
import re

User = get_user_model()


class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Correo Electrónico",
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Correo electrónico"}),
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Contraseña"}),
    )


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
