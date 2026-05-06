from core.models import Clase, Asistencia
from django.core.exceptions import ObjectDoesNotExist

# Ver listado de presentes
def obtener_presentes_por_clase(clase_id):
    return Asistencia.objects.filter(clase_id=clase_id, presente=True)

# ubicacion para verlo http://127.0.0.1:8000/clase/1/presentes/

# Cancelar clase (Sin terminar)
def cancelar_clase_servicio(clase_id):
    try:
        clase = Clase.objects.get(id=clase_id)
        clase.activa = False
        clase.save()
        return {"success": True, "message": f"Clase {clase_id} cancelada con éxito."}
    except ObjectDoesNotExist:
        return {"success": False, "message": "La clase no existe."}