
from django import forms
from turno.models import Actividad

class CompraPaqueteForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Traemos todas las actividades disponibles dinámicamente
        actividades = Actividad.objects.all()
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