from django.urls import path
from . import views

urlpatterns = [
    path('clase/<int:clase_id>/presentes/', views.api_lista_presentes, name='api_presentes'),
    path('clase/<int:clase_id>/cancelar/', views.api_cancelar_clase, name='api_cancelar'),
]