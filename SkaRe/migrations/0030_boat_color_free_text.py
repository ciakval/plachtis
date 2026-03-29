from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SkaRe', '0029_organizer_add_wants_small_hat'),
    ]

    operations = [
        migrations.AlterField(
            model_name='boat',
            name='hull_color',
            field=models.CharField(max_length=50, verbose_name='hull color'),
        ),
        migrations.AlterField(
            model_name='boat',
            name='sail_color',
            field=models.CharField(max_length=50, verbose_name='sail color'),
        ),
    ]
