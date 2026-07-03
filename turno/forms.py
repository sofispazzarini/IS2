from django import forms
from django.utils import timezone
from datetime import timedelta, datetime

# CAMBIADO: Se agregó Salon a las importaciones
from .models import Clase, Salon
from user.models import Profesor
from actividad.models import Actividad


class ClaseForm(forms.ModelForm):
    salon = forms.ModelChoiceField(
        queryset=Salon.objects.all(),
        empty_label=None,
        widget=forms.Select(attrs={'class': 'form-input'})
    )

    es_recurrente = forms.BooleanField(
        required=False,
        label="Repetir semanalmente hasta fin de mes",
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'})
    )

    class Meta:
        model = Clase
        fields = ['actividad', 'profesor', 'fecha', 'hora_inicio', 'cupo_maximo', 'salon']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'hora_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'form-input'}),
            'cupo_maximo': forms.NumberInput(attrs={'class': 'form-input', 'min': 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['actividad'].queryset = Actividad.objects.filter(activa=True)
        self.fields['profesor'].queryset = Profesor.objects.filter(activo=True)
        self.fields['salon'].label_from_instance = lambda obj: f"{obj.nombre} (Capacidad 50 cupos)"

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
        salon = cleaned_data.get('salon') # Trae la instancia del objeto Salon seleccionada
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

        # 🕒 VALIDACIÓN DE RANGO HORARIO (Escenario V)
        from datetime import time
        hora_minima = time(8, 0)
        hora_maxima = time(19, 0)
        
        if not (hora_minima <= hora_inicio <= hora_maxima):
            raise forms.ValidationError("Elegir un horario entre las 8:00 y 19:00hs")

        hora_fin = (datetime.combine(fecha, hora_inicio) + timedelta(hours=1)).time()
        cleaned_data['hora_fin'] = hora_fin

        clase_actual_id = self.instance.pk if self.instance else None

        # 📋 LISTA PARA ACUMULAR LOS ERRORES
        errores_globales = []

        # 1. Validación de Salón
        # NUEVO: Al comparar salon=salon, Django busca mediante la ForeignKey de forma limpia
        conficto_salon = Clase.objects.filter(
            fecha=fecha,
            salon=salon,
            cancelada=False,
            hora_inicio__lt=hora_fin,
            hora_fin__gt=hora_inicio
        ).exclude(pk=clase_actual_id).exists()

        if conficto_salon:
            errores_globales.append(
                f"Salón no disponible para el {fecha.strftime('%d/%m/%Y')} a las {hora_inicio.strftime('%H:%M')} hs."
            )

        # 2. Validación de Profesor
        conflicto_profesor = Clase.objects.filter(
            fecha=fecha,
            profesor=profesor,
            cancelada=False,
            hora_inicio__lt=hora_fin,
            hora_fin__gt=hora_inicio
        ).exclude(pk=clase_actual_id).exists()

        if conflicto_profesor:
            errores_globales.append(
                f"Profesor no disponible para el {fecha.strftime('%d/%m/%Y')} a las {hora_inicio.strftime('%H:%M')} hs."
            )

        # 🚨 SI SE JUNTÓ ALGÚN ERROR, LOS MANDAMOS TODOS DE UNA
        if errores_globales:
            raise forms.ValidationError(errores_globales)

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