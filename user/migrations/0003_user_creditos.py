from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0002_user_fecha_nacimiento'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='creditos',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
