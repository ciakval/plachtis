from django.db import migrations


def create_infodesk_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name='InfoDesk')


def delete_infodesk_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='InfoDesk').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('SkaRe', '0014_boat'),
    ]

    operations = [
        migrations.RunPython(create_infodesk_group, delete_infodesk_group),
    ]
