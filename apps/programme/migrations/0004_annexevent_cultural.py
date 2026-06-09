from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("programme", "0003_communication_kind"),
    ]

    operations = [
        migrations.AlterField(
            model_name="annexevent",
            name="kind",
            field=models.CharField(
                choices=[
                    ("break", "Pause"),
                    ("meal", "Repas"),
                    ("plenary", "Plénière"),
                    ("cultural", "Événement culturel"),
                    ("other", "Autre"),
                ],
                default="other",
                max_length=10,
                verbose_name="Type",
            ),
        ),
    ]
