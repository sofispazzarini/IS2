from django.urls import path
from . import views

app_name = 'resena'

urlpatterns = [
    path('crear/', views.crear_resena, name='crear'),                      # reseña del centro (no tocar)
    path('crear-clase/<int:clase_id>/', views.crear_resena_clase, name='crear_clase'),  # reseña de clase (nueva)
    path('eliminar/<int:resena_id>/', views.eliminar_resena, name='eliminar'),
    path('editar/<int:resena_id>/', views.editar_resena, name='editar'),
]
