from django.contrib import admin
from .models import Clase, Profesor, Actividad

admin.site.register(Clase)
admin.site.register(Profesor)
admin.site.register(Actividad)