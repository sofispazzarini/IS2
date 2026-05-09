from django.urls import path
from . import views

app_name = "user"

urlpatterns = [
    path("registro/", views.registro, name="registro"),
    path('login/', views.login_view, name='login'),
    path('register/', views.registro, name='register'),
]

