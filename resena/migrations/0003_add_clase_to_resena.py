from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resena', '0002_initial'),
        ('turno', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='resena',
            name='clase',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.CASCADE, related_name='resenas', to='turno.clase'),
        ),
    ]
