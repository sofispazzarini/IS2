from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0003_user_creditos'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistorialUsuarioBaja',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('apellido', models.CharField(max_length=100)),
                ('email', models.EmailField(max_length=254)),
                ('dni', models.CharField(max_length=20)),
                ('telefono', models.CharField(max_length=20)),
                ('fecha_nacimiento', models.DateField(blank=True, null=True)),
                ('fecha_registro_original', models.DateTimeField()),
                ('creditos_al_momento', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('fecha_baja', models.DateTimeField(auto_now_add=True)),
                ('motivo', models.TextField(blank=True)),
                ('dado_baja_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bajas_realizadas', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
