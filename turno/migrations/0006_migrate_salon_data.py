# Generated migration to populate Salon table from existing Clase.salon values

from django.db import migrations, models
import django.db.models.deletion


def populate_salons(apps, schema_editor):
    """Populate Salon table from existing Clase.salon values"""
    Clase = apps.get_model('turno', 'Clase')
    Salon = apps.get_model('turno', 'Salon')
    
    # Get all unique salon values
    unique_salons = set(Clase.objects.values_list('salon', flat=True).distinct())
    
    # Create Salon records
    for salon_name in unique_salons:
        if salon_name:  # Skip None/empty values
            salon_obj, created = Salon.objects.get_or_create(
                nombre=salon_name
            )


def reverse_populate_salons(apps, schema_editor):
    """Reverse: delete Salon records created from Clase migration"""
    # We won't delete them as they might be referenced elsewhere
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('turno', '0005_salon'),
    ]

    operations = [
        migrations.RunPython(populate_salons, reverse_populate_salons),
    ]
