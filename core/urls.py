from django.urls import path
from .views import home, mantenimiento

app_name = 'core'

urlpatterns = [
    path('', home, name='home'),
    path('maintenance/', mantenimiento, name='maintenance'),
]