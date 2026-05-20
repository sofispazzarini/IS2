from django import forms
from .models import Actividad


class ActividadForm(forms.ModelForm):
    class Meta:
        model = Actividad
        fields = ['nombre', 'descripcion', 'precio', 'activa']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'precio': forms.NumberInput(attrs={'class': 'form-input', 'min': 0, 'step': '0.01'}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
        labels = {
            'activa': 'Activa',
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.duracion_min = 60
        if commit:
            instance.save()
        return instance
