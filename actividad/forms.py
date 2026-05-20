from django import forms
from .models import Actividad


class ActividadForm(forms.ModelForm):
    class Meta:
        model = Actividad
        fields = ['nombre', 'descripcion', 'duracion_min', 'precio', 'activa']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'duracion_min': forms.NumberInput(attrs={'class': 'form-input', 'min': 1}),
            'precio': forms.NumberInput(attrs={'class': 'form-input', 'min': 0, 'step': '0.01'}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
        labels = {
            'duracion_min': 'Duración (minutos)',
            'activa': 'Activa',
        }
