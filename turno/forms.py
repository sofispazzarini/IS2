from django import forms
from django.utils import timezone
from datetime import timedelta, datetime

from .models import Clase
from user.models import Profesor
from actividad.models import Actividad


class ClaseForm(forms.ModelForm):
    class Meta:
        model = Clase
        fields = ['actividad', 'profesor', 'fecha', 'hora_inicio', 'cupo_maximo', 'salon']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'hora_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'form-input'}),
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
        hoy = timezone.localdate()
        if fecha and fecha < hoy:
            raise forms.ValidationError("No puedes crear una clase para una fecha pasada.")
        return fecha

    def clean(self):
        cleaned_data = super().clean()
        fecha = cleaned_data.get('fecha')
        hora_inicio = cleaned_data.get('hora_inicio')
        salon = cleaned_data.get('salon')
        profesor = cleaned_data.get('profesor')

        if not all([fecha, hora_inicio, salon, profesor]):
            return cleaned_data
        
        # 🛡️ VALIDACIÓN UNIFICADA DE TIEMPO (FECHA Y HORA JUNTAS)
        momento_clase = datetime.combine(fecha, hora_inicio)
        ahora_local = timezone.localtime(timezone.now()).replace(tzinfo=None)

        # Si el momento combinado de la clase ya pasó (sea ayer, o sea hoy hace una hora)
        if momento_clase < ahora_local:
            raise forms.ValidationError(
                "No puedes crear una clase para una fecha ya pasada."
            )

        hora_fin = (datetime.combine(fecha, hora_inicio) + timedelta(hours=1)).time()
        cleaned_data['hora_fin'] = hora_fin

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
                f"Salón no disponible para el {fecha.strftime('%d/%m/%Y')} a las {hora_inicio.strftime('%H:%M')} hs."
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
                f"Profesor no disponible para el {fecha.strftime('%d/%m/%Y')} a las {hora_inicio.strftime('%H:%M')} hs."
            )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        hora_fin = self.cleaned_data.get('hora_fin')
        if hora_fin:
            instance.hora_fin = hora_fin
        if commit:
            instance.save()
        return instance
    
    def clean_cupo_maximo(self):
        cupo = self.cleaned_data.get('cupo_maximo')
        if cupo is not None and cupo <= 0:
            raise forms.ValidationError("La clase debe contar como mínimo con 1 cupo.")
        if cupo is not None and cupo > 50:
            raise forms.ValidationError("El cupo máximo permitido por salón es de 50 personas.")
        return cupo
