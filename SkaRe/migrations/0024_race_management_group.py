from django.db import migrations


def create_race_management_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name='RaceManagement')


def delete_race_management_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='RaceManagement').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('SkaRe', '0023_merge_0019_hat_size_split_0022_review_fixes'),
    ]

    operations = [
        migrations.RunPython(create_race_management_group, delete_race_management_group),
    ]
