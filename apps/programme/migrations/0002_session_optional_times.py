from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("programme", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="session",
            name="start_time",
            field=models.TimeField(null=True, blank=True, verbose_name="Début"),
        ),
        migrations.AlterField(
            model_name="session",
            name="end_time",
            field=models.TimeField(null=True, blank=True, verbose_name="Fin"),
        ),
        migrations.AlterModelOptions(
            name="session",
            options={"ordering": ["date", "order", "start_time"], "verbose_name": "Session", "verbose_name_plural": "Sessions"},
        ),
    ]
