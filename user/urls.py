from django.urls import path
from . import views

app_name = "user"

urlpatterns = [
    path("registro/", views.registro, name="registro"),
    path('login/', views.registro, name='login'),
    path('register/', views.register_view, name='register'),
]

