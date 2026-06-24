from django.db import models


class ConfiguracionSistema(models.Model):
    modo_mantenimiento = models.BooleanField(default=False)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración del sistema"
        verbose_name_plural = "Configuraciones del sistema"

    @classmethod
    def obtener(cls):
        configuracion, created = cls.objects.get_or_create(
            pk=1,
            defaults={'modo_mantenimiento': False}
        )
        return configuracion

    def __str__(self):
        return f"Modo mantenimiento {'activo' if self.modo_mantenimiento else 'desactivado'}"
