from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("programme", "0002_session_optional_times"),
    ]

    operations = [
        migrations.AddField(
            model_name="communication",
            name="kind",
            field=models.CharField(
                choices=[
                    ("talk", "Communication"),
                    ("qa", "Questions/Réponses"),
                    ("discussion", "Discussion"),
                    ("intro", "Introduction"),
                ],
                default="talk",
                max_length=20,
                verbose_name="Type",
            ),
        ),
    ]
