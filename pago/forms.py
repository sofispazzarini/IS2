
from django import forms
from actividad.models import Actividad

DIAS_SEMANA = [
    ('0', 'Lunes'),
    ('1', 'Martes'),
    ('2', 'Miércoles'),
    ('3', 'Jueves'),
    ('4', 'Viernes'),
    ('5', 'Sábado'),
    ('6', 'Domingo'),
]

class CompraPaqueteForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        actividades = Actividad.objects.filter(activa=True)
        for actividad in actividades:
            self.fields[f'actividad_{actividad.id}'] = forms.IntegerField(
                label=f"{actividad.nombre} (${actividad.precio} c/u)",
                min_value=0,
                initial=0,
                widget=forms.NumberInput(attrs={
                    'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-bordo-500 focus:border-bordo-500 cantidad-actividad',
                    'data-precio': actividad.precio
                })
            )
            self.fields[f'dias_{actividad.id}'] = forms.MultipleChoiceField(
                label=f"Días fijos para {actividad.nombre}",
                choices=DIAS_SEMANA,
                required=False,
                widget=forms.CheckboxSelectMultiple(attrs={
                    'class': 'dias-checkbox'
                })
            )