import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('actividad', '0002_initial'),
        ('turno', '0004_alter_clase_actividad_alter_clase_profesor'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='reserva',
            name='monto_pagado',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.CreateModel(
            name='TurnoFijo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dia_semana', models.IntegerField(choices=[(0, 'Lunes'), (1, 'Martes'), (2, 'Miércoles'), (3, 'Jueves'), (4, 'Viernes'), (5, 'Sábado'), (6, 'Domingo')])),
                ('hora_inicio', models.TimeField()),
                ('activo', models.BooleanField(default=True)),
                ('actividad', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='turnos_fijos', to='actividad.actividad')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='turnos_fijos', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('usuario', 'dia_semana', 'hora_inicio')},
            },
        ),
        migrations.CreateModel(
            name='Abono',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mes', models.IntegerField()),
                ('anio', models.IntegerField()),
                ('cantidad_turnos_fijos', models.IntegerField()),
                ('descuento_porcentaje', models.IntegerField(default=0)),
                ('monto_total', models.DecimalField(decimal_places=2, max_digits=10)),
                ('monto_final', models.DecimalField(decimal_places=2, max_digits=10)),
                ('metodo_pago', models.CharField(choices=[('tarjeta', 'Tarjeta'), ('efectivo', 'Efectivo'), ('posnet', 'POSNET'), ('transferencia', 'Transferencia')], default='tarjeta', max_length=30)),
                ('estado_pago', models.CharField(choices=[('pendiente', 'Pendiente'), ('aprobado', 'Aprobado'), ('rechazado', 'Rechazado')], default='pendiente', max_length=30)),
                ('fecha_pago', models.DateTimeField(auto_now_add=True)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='abonos', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('usuario', 'mes', 'anio')},
            },
        ),
        migrations.AddField(
            model_name='reserva',
            name='abono',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reservas', to='turno.abono'),
        ),
    ]