from django.urls import path
from . import views

app_name = 'resena'

urlpatterns = [
    path('crear/', views.crear_resena, name='crear'),
    path('eliminar/<int:resena_id>/', views.eliminar_resena, name='eliminar'),
    path('editar/<int:resena_id>/', views.editar_resena, name='editar'),
]
