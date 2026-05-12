from django import forms
from .models import Clase

class ClaseForm(forms.ModelForm):
    class Meta:
        model = Clase
        fields = ['actividad', 'profesor', 'fecha', 'hora_inicio', 'hora_fin', 'cupo_maximo', 'salon']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-bordo-500 focus:border-bordo-500'}),
            'hora_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-bordo-500 focus:border-bordo-500'}),
            'hora_fin': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-bordo-500 focus:border-bordo-500'}),
            'actividad': forms.Select(attrs={'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-bordo-500'}),
            'profesor': forms.Select(attrs={'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-bordo-500'}),
            'cupo_maximo': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-bordo-500'}),
            'salon': forms.TextInput(attrs={'placeholder': 'Ej: Salón 3', 'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-bordo-500'}),
        }