from django import forms
from .models import Resena


class ResenaForm(forms.ModelForm):
    """Formulario para crear reseñas con validaciones de negocio."""
    
    # Palabras no permitidas (lista de control)
    PALABRAS_NO_PERMITIDAS = ['malo', 'terrible', 'horrible', 'pésimo', 'mediocre', 'estafa', 'puto', 'putos', 'pelotudo', 'pelotudos', 'put0', 'put0s', 'pu7os', 'forro', 'forros']
    
    comentario = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Comparte tu experiencia (máximo 60 caracteres)',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-bordo-700',
        }),
        label='Tu reseña',
        required=True,
    )
    
    class Meta:
        model = Resena
        fields = ['comentario']
        # Quitar el max_length automático para controlar el mensaje
        widgets = {
            'comentario': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Comparte tu experiencia (máximo 60 caracteres)',
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-bordo-700',
            })
        }
    
    def clean_comentario(self):
        """Validar comentario: longitud y palabras no permitidas."""
        comentario = self.cleaned_data.get('comentario', '').strip()
        
        if not comentario:
            raise forms.ValidationError('La reseña no puede estar vacía.')
        
        # Validar palabras no permitidas PRIMERO (según el orden de escenarios)
        comentario_lower = comentario.lower()
        palabras_encontradas = [
            palabra for palabra in self.PALABRAS_NO_PERMITIDAS
            if palabra in comentario_lower
        ]
        
        if palabras_encontradas:
            raise forms.ValidationError(
                'Se utilizaron palabras no permitidas.'
            )
        
        # Validar longitud (máximo 60 caracteres)
        if len(comentario) > 60:
            raise forms.ValidationError(
                'La reseña no puede ser enviada por exceso de caracteres.'
            )
        
        return comentario

