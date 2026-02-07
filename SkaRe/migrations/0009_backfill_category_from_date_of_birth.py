# Generated migration to backfill category from date_of_birth

from django.db import migrations
from datetime import date


def calculate_category_from_dob(date_of_birth, reference_date=None):
    """
    Calculate scout category based on date of birth year only.
    Uses the same logic as Person.calculate_category()
    
    Age groups (based on year only):
    - CUB: up to 12 years old (age <= 12)
    - SCOUT: up to 15 years old (age <= 15)
    - ROVER: up to 18 years old (age <= 18)
    - ADULT: 19 and over (age >= 19)
    """
    if not date_of_birth:
        return None
    
    if reference_date is None:
        # Use current date as reference
        reference_date = date.today()
    
    # Calculate age based on year only (no month/day adjustment)
    birth_year = date_of_birth.year
    reference_year = reference_date.year
    age = reference_year - birth_year
    
    # Determine category based on age (year-based only)
    if age <= 12:
        return 'CUB'
    elif age <= 15:
        return 'SCOUT'
    elif age <= 18:
        return 'ROVER'
    else:
        return 'ADULT'


def backfill_categories(apps, schema_editor):
    """Backfill category for all Person records based on date_of_birth."""
    Person = apps.get_model('SkaRe', 'Person')
    EventSettings = apps.get_model('SkaRe', 'EventSettings')
    
    # Try to get event date, otherwise use current date
    try:
        event_settings = EventSettings.objects.first()
        if event_settings and event_settings.registration_deadline:
            reference_date = event_settings.registration_deadline.date()
        else:
            reference_date = date.today()
    except:
        reference_date = date.today()
    
    # Update all Person records
    for person in Person.objects.filter(date_of_birth__isnull=False):
        if person.date_of_birth:
            calculated_category = calculate_category_from_dob(person.date_of_birth, reference_date)
            if calculated_category:
                person.category = calculated_category
                person.save(update_fields=['category'])


def reverse_backfill(apps, schema_editor):
    """Reverse migration - set all categories to None."""
    Person = apps.get_model('SkaRe', 'Person')
    Person.objects.all().update(category=None)


class Migration(migrations.Migration):

    dependencies = [
        ('SkaRe', '0008_merge_20260206_2157'),
    ]

    operations = [
        migrations.RunPython(backfill_categories, reverse_backfill),
    ]
