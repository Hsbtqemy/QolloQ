from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0011_bilingual_support"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="from_name",
            field=models.CharField(
                blank=True,
                max_length=100,
                verbose_name="Nom d'expéditeur",
                help_text="Affiché dans la boîte de réception à la place du nom de l'événement. Ex. : « Jean Dupont — Colloque 2026 ».",
            ),
        ),
    ]
