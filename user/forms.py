from django import forms
from django.contrib.auth import get_user_model
from datetime import date
import re

from .models import Profesor

User = get_user_model()


class ProfesorForm(forms.ModelForm):
    class Meta:
        model = Profesor
        # 🆕 Agregamos 'dni' a la lista de campos
        fields = ['nombre', 'apellido', 'dni', 'telefono', 'email', 'especialidad', 'descripcion', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input'}),
            'apellido': forms.TextInput(attrs={'class': 'form-input'}),
            # 🛡️ Blindamos el input de DNI contra signos, letras y decimales
            'dni': forms.NumberInput(attrs={
                'class': 'form-input', 
                'min': '0',
                'onkeydown': "if(['-', '+', 'e', 'E', '.', ','].includes(event.key)) event.preventDefault();"
            }),
            'telefono': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '0',
                'onkeydown': "if(['-', '+', 'e', 'E', '.', ','].includes(event.key)) event.preventDefault();"
            }),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'especialidad': forms.TextInput(attrs={'class': 'form-input'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        
        # 1. Si el email viene vacío (y tu modelo lo permite), no validamos nada
        if not email:
            return email
            
        # 2. Buscamos si ya existe algún profesor con este correo
        queryset = Profesor.objects.filter(email=email)
        
        # 3. Regla clave: Si estamos EDITANDO, excluimos al profesor actual 
        # para que no choque con su propio correo.
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
            
        # 4. Si el queryset todavía tiene algún resultado, tiramos el error
        if queryset.exists():
            raise forms.ValidationError("Error: Ya existe un profesor asociado al correo electrónico ingresado.")
            
        return email

    # 🛡️ VALIDACIÓN EN EL BACKEND PARA EVITAR REPETIDOS
    def clean_dni(self):
        dni = self.cleaned_data.get('dni')

        # Filtramos por el DNI ingresado
        queryset = Profesor.objects.filter(dni=dni)

        # Si ya existe la instancia (estamos modificando), nos excluimos de la búsqueda
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise forms.ValidationError(f"Error: Ya existe un profesor asociado al DNI {dni}.")

        return dni

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        if telefono:
            telefono_str = str(telefono).replace(" ", "")
            if not telefono_str.isdigit():
                raise forms.ValidationError("El teléfono solo puede contener números.")
        return telefono


class EditarPerfilForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "telefono"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre"}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Apellido"}),
            "telefono": forms.TextInput(attrs={
                "class": "form-control", 
                "placeholder": "Teléfono",
                "inputmode": "numeric",
                "pattern": "[0-9]*",
                "oninput": "this.value=this.value.replace(/[^0-9]/g,'')"
            }),
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
            raise forms.ValidationError("El nombre solo puede contener letras")
        return first_name.strip()

    def clean_last_name(self):
        last_name = self.cleaned_data.get("last_name")
        if not last_name or not last_name.strip():
            raise forms.ValidationError("El campo apellido es obligatorio")
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$', last_name):
            raise forms.ValidationError("El apellido solo puede contener letras")
        return last_name.strip()

    def clean_telefono(self):
        telefono = self.cleaned_data.get("telefono")
        if telefono:
            if not re.match(r'^\d+$', telefono):
                raise forms.ValidationError("El teléfono solo puede contener números")
        return telefono


class EditarClienteForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "dni", "telefono"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre"}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Apellido"}),
            "dni": forms.TextInput(attrs={"class": "form-control", "placeholder": "DNI"}),
            "telefono": forms.TextInput(attrs={"class": "form-control", "placeholder": "Teléfono"}),
        }
        labels = {
            "first_name": "Nombre",
            "last_name": "Apellido",
            "dni": "DNI",
            "telefono": "Teléfono",
        }

    def __init__(self, *args, **kwargs):
        self.client = kwargs.pop('client', None)
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

    def clean_dni(self):
        dni = self.cleaned_data.get("dni")
        if dni:
            if self.client:
                if User.objects.filter(dni=dni).exclude(pk=self.client.pk).exists():
                    raise forms.ValidationError("Este DNI ya está registrado por otro usuario")
        return dni

    def clean_telefono(self):
        telefono = self.cleaned_data.get("telefono")
        if telefono:
            if not re.match(r'^\d+$', telefono):
                raise forms.ValidationError("El teléfono solo puede contener números")
            if self.client:
                if User.objects.filter(telefono=telefono).exclude(pk=self.client.pk).exists():
                    raise forms.ValidationError("Este teléfono ya está registrado por otro usuario")
        return telefono


class CrearSecretarioForm(forms.ModelForm):
    """Formulario para crear un nuevo secretario."""
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Contraseña"}),
        min_length=8,
        help_text="Mínimo 8 caracteres"
    )
    password_confirm = forms.CharField(
        label="Confirmar Contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirmar contraseña"}),
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "dni", "telefono"]
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
            "email": "Correo electrónico",
            "dni": "DNI",
            "telefono": "Teléfono",
        }

    def clean_first_name(self):
        first_name = self.cleaned_data.get("first_name")
        if not first_name or not first_name.strip():
            raise forms.ValidationError("El campo nombre es obligatorio")
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$', first_name):
            raise forms.ValidationError("El nombre solo puede contener letras")
        return first_name.strip()

    def clean_last_name(self):
        last_name = self.cleaned_data.get("last_name")
        if not last_name or not last_name.strip():
            raise forms.ValidationError("El campo apellido es obligatorio")
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$', last_name):
            raise forms.ValidationError("El apellido solo puede contener letras")
        return last_name.strip()

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado")
        return email

    def clean_dni(self):
        dni = self.cleaned_data.get("dni")
        if dni:
            if User.objects.filter(dni=dni).exists():
                raise forms.ValidationError("Este DNI ya está registrado")
        return dni

    def clean_telefono(self):
        telefono = self.cleaned_data.get("telefono")
        if telefono:
            if not re.match(r'^\d+$', telefono):
                raise forms.ValidationError("El teléfono solo puede contener números")
        return telefono

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if len(password) < 8:
            raise forms.ValidationError("La contraseña debe tener mínimo 8 caracteres")
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("No coinciden")
        
        return cleaned_data


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
    current_password = forms.CharField(
        label="Contraseña actual",
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Contraseña actual"}),
    )
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

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        current = self.cleaned_data.get('current_password')
        if not current:
            raise forms.ValidationError("Completar contraseña")
        if self.user and not self.user.check_password(current):
            raise forms.ValidationError("La contraseña actual es incorrecta")
        return current

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if not password:
            raise forms.ValidationError("Completar contraseña")
        if len(password) < 8 or len(password) > 20:
            raise forms.ValidationError("La contraseña debe tener entre 8 y 20 caracteres")
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        # Si falta alguno, error de campos vacíos
        if not password or not password_confirm:
            raise forms.ValidationError("Las contraseñas no coinciden")

        # Si ambos están completos pero no coinciden, error de no coincidencia
        if password and password_confirm and password != password_confirm:
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
        if dni and not dni.isdigit():
            raise forms.ValidationError("DNI debe contener solo números")
        if dni and User.objects.filter(dni=dni).exists():
            raise forms.ValidationError("DNI ya asociado a una cuenta, vuelva a intentarlo")
        return dni

    def clean_telefono(self):
        telefono = self.cleaned_data.get("telefono")
        if telefono:
            telefono_sin_espacios = telefono.replace(" ", "")
            if not telefono_sin_espacios.isdigit():
                raise forms.ValidationError("Teléfono debe contener solo números")
        return telefono

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

class RestablecerContrasenaForm(forms.Form):
    new_password1 = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    new_password2 = forms.CharField(
        label="Confirmar nueva contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )

    def clean_new_password1(self):
        password = self.cleaned_data.get("new_password1")
        if password and (len(password) < 8 or len(password) > 20):
            raise forms.ValidationError(
                "Tu contraseña debe tener entre 8 y 20 caracteres, vuelva a intentarlo."
            )
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("new_password1")
        password_confirm = cleaned_data.get("new_password2")

        # Cambiamos esto para que el error se clave directo en el campo "new_password2"
        if password and password_confirm and password != password_confirm:
            self.add_error('new_password2', "Las contraseñas no coinciden, vuelva a intentarlo")

        return cleaned_data