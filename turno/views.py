from django.shortcuts import render


def reservas_view(request):
    return render(request, 'turno/reservas.html')