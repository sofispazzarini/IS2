from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('turno', '0500_abono_turnofijo_reserva'),
    ]

    operations = [
        migrations.AddField(
            model_name='abono',
            name='preference_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='abono',
            name='payment_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='abono',
            name='reservas_origen_ids',
            field=models.TextField(blank=True, null=True),
        ),
    ]