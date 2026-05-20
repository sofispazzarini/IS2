from django import forms
from django.utils import timezone

from .models import Clase
from user.models import Profesor
from actividad.models import Actividad


class ClaseForm(forms.ModelForm):
    class Meta:
        model = Clase
        fields = ['actividad', 'profesor', 'fecha', 'hora_inicio', 'hora_fin', 'cupo_maximo', 'salon']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'hora_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'form-input'}),
            'hora_fin': forms.TimeInput(attrs={'type': 'time', 'class': 'form-input'}),
            'cupo_maximo': forms.NumberInput(attrs={'class': 'form-input', 'min': 1}),
            'salon': forms.TextInput(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['actividad'].queryset = Actividad.objects.filter(activa=True)
        self.fields['profesor'].queryset = Profesor.objects.filter(activo=True)

        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-input')

    def clean_fecha(self):
        fecha = self.cleaned_data.get('fecha')
        if fecha and fecha < timezone.now().date():
            raise forms.ValidationError("No puedes crear una actividad para una fecha pasada.")
        return fecha

    def clean(self):
        cleaned_data = super().clean()
        fecha = cleaned_data.get('fecha')
        hora_inicio = cleaned_data.get('hora_inicio')
        hora_fin = cleaned_data.get('hora_fin')
        salon = cleaned_data.get('salon')
        profesor = cleaned_data.get('profesor')

        if not all([fecha, hora_inicio, salon, profesor]):
            return cleaned_data

        clase_actual_id = self.instance.pk if self.instance else None

        conflicto_salon = Clase.objects.filter(
            fecha=fecha,
            salon=salon,
            cancelada=False,
            hora_inicio__lt=hora_fin,
            hora_fin__gt=hora_inicio
        ).exclude(pk=clase_actual_id).exists()

        if conflicto_salon:
            raise forms.ValidationError(
                f"Salón no disponible para el {fecha.strftime('%d/%m/%Y')} a las {hora_inicio.strftime('%H:%S')} hs."
            )

        conflicto_profesor = Clase.objects.filter(
            fecha=fecha,
            profesor=profesor,
            cancelada=False,
            hora_inicio__lt=hora_fin,
            hora_fin__gt=hora_inicio
        ).exclude(pk=clase_actual_id).exists()

        if conflicto_profesor:
            raise forms.ValidationError(
                f"Profesor no disponible para el {fecha.strftime('%d/%m/%Y')} a las {hora_inicio.strftime('%H:%S')} hs."
            )

        return cleaned_data
