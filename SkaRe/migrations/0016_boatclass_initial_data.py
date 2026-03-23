from django.db import migrations


SAIL_CLASSES = [
    ('P550', False),
    ('420', False),
    ('Cadet', False),
    ('Fireball', False),
    ('Evropa', False),
    ('Optimist', False),
    ('Finn', False),
    ('Ostatní plachetnice', True),   # Other (sail)
]

OTHER_CLASSES = [
    ('paddleboard', False),
    ('windsurf', False),
    ('canoe', False),
    ('motorboat', False),
    ('seakayak', False),
    ('Ostatní', True),              # Other (other)
]


def seed_boat_classes(apps, schema_editor):
    BoatClass = apps.get_model('SkaRe', 'BoatClass')
    for order, (name, is_other) in enumerate(SAIL_CLASSES, start=1):
        BoatClass.objects.get_or_create(
            name=name,
            defaults={'category': 'SAIL', 'is_other': is_other, 'order': order},
        )
    for order, (name, is_other) in enumerate(OTHER_CLASSES, start=len(SAIL_CLASSES) + 1):
        BoatClass.objects.get_or_create(
            name=name,
            defaults={'category': 'OTHER', 'is_other': is_other, 'order': order},
        )


def delete_boat_classes(apps, schema_editor):
    BoatClass = apps.get_model('SkaRe', 'BoatClass')
    names = [n for n, _ in SAIL_CLASSES + OTHER_CLASSES]
    BoatClass.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('SkaRe', '0015_infodesk_group'),
    ]

    operations = [
        migrations.RunPython(seed_boat_classes, delete_boat_classes),
    ]
