from django.contrib import admin
from .models import User, Clase, Asistencia, Profesor

admin.site.register(User)
admin.site.register(Clase)
admin.site.register(Profesor)
admin.site.register(Asistencia)

# python manage.py runserver
# http://127.0.0.1:8000/admin/