# Generated migration to convert salon from CharField to ForeignKey

from django.db import migrations, models
import django.db.models.deletion


def migrate_salon_to_fk(apps, schema_editor):
    """Map existing Clase.salon string values to Salon FK"""
    Clase = apps.get_model('turno', 'Clase')
    Salon = apps.get_model('turno', 'Salon')
    
    # Build mapping from salon name to ID
    salon_name_to_id = {}
    for salon in Salon.objects.all():
        salon_name_to_id[salon.nombre] = salon.id
    
    # Query raw data and update with FK IDs
    cursor = schema_editor.connection.cursor()
    cursor.execute("SELECT id, salon FROM turno_clase WHERE salon IS NOT NULL")
    rows = cursor.fetchall()
    
    for clase_id, salon_name in rows:
        if salon_name in salon_name_to_id:
            salon_id = salon_name_to_id[salon_name]
            cursor.execute(
            "UPDATE turno_clase SET salon_id = %s WHERE id = %s",
            [salon_id, clase_id]
            )


class Migration(migrations.Migration):

    dependencies = [
        ('turno', '0006_migrate_salon_data'),
    ]

    operations = [
        # First add the new FK column as nullable
        migrations.AddField(
            model_name='clase',
            name='salon_id',
            field=models.BigIntegerField(null=True, blank=True),
        ),
        # Migrate data from salon string to salon_id FK
        migrations.RunPython(migrate_salon_to_fk, migrations.RunPython.noop),
        # Remove the old CharField
        migrations.RemoveField(
            model_name='clase',
            name='salon',
        ),
        # Convert the temporary integer field to a proper FK
        migrations.RenameField(
            model_name='clase',
            old_name='salon_id',
            new_name='salon_temp',
        ),
        migrations.AddField(
            model_name='clase',
            name='salon',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='clases', to='turno.salon', null=True),
        ),
        migrations.RunPython(
            lambda apps, schema_editor: schema_editor.execute(
                "UPDATE turno_clase SET salon_id = salon_temp WHERE salon_temp IS NOT NULL"
            ),
            migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name='clase',
            name='salon_temp',
        ),
        # Make salon NOT NULL
        migrations.AlterField(
            model_name='clase',
            name='salon',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='clases', to='turno.salon'),
        ),
    ]
