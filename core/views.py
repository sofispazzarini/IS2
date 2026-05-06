from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Clase
# Importamos AMBAS funciones del archivo de servicios
from .services.services import obtener_presentes_por_clase, cancelar_clase_servicio

def api_lista_presentes(request, clase_id):
    get_object_or_404(Clase, id=clase_id)
    presentes = obtener_presentes_por_clase(clase_id)
    
    data = []
    for p in presentes:
        data.append({
            "id": p.usuario.id,
            "dni": p.usuario.DNI,
            "nombre_completo": f"{p.usuario.nombre} {p.usuario.apellido}",
            "fecha_registro": p.fecha_registro.strftime("%Y-%m-%d %H:%M:%S")
        })
    return JsonResponse({"total": len(data), "estudiantes": data})

def api_cancelar_clase(request, clase_id):
    # Llamamos a la función de cancelar
    resultado = cancelar_clase_servicio(clase_id)
    return JsonResponse(resultado)