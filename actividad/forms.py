from django import forms
from .models import Actividad


class ActividadForm(forms.ModelForm):
    # Forzamos a que el precio renderice siempre con punto decimal puro en el HTML
    precio = forms.DecimalField(
        localize=False, 
        widget=forms.NumberInput(attrs={'class': 'form-input', 'min': '0', 'step': '0.01'})
    )

    class Meta:
        model = Actividad
        fields = ['nombre', 'descripcion', 'precio']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
        labels = {
            'activa': 'Activa',
        }

    # 🛡️ COPIÁ ESTO ACÁ: Validación de nombre único (ignorando mayúsculas/minúsculas)
    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        
        # Buscamos si ya existe una actividad con ese nombre (case-insensitive)
        queryset = Actividad.objects.filter(nombre__iexact=nombre)
        
        # Si estamos editando, excluimos la actividad actual para que deje guardar otros cambios
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
            
        if queryset.exists():
            raise forms.ValidationError(
                f"Ya existe una actividad con el nombre '{nombre}'."
            )
            
        return nombre

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.duracion_min = 60
        if commit:
            instance.save()
        return instance