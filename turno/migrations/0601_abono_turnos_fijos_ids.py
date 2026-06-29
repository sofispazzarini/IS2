from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('turno', '0600_abono_mp_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='abono',
            name='turnos_fijos_ids',
            field=models.TextField(blank=True, null=True),
        ),
    ]