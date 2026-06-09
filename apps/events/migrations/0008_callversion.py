import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0007_event_site_customization"),
    ]

    operations = [
        migrations.CreateModel(
            name="CallVersion",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Créé le"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Modifié le"),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Supprimé le"
                    ),
                ),
                (
                    "language",
                    models.CharField(
                        choices=[
                            ("fr", "Français"),
                            ("en", "English"),
                            ("de", "Deutsch"),
                            ("es", "Español"),
                            ("it", "Italiano"),
                            ("pt", "Português"),
                        ],
                        max_length=5,
                        verbose_name="Langue",
                    ),
                ),
                (
                    "content",
                    models.TextField(blank=True, verbose_name="Appel à communications"),
                ),
                (
                    "bibliography",
                    models.TextField(blank=True, verbose_name="Bibliographie"),
                ),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="call_versions",
                        to="events.event",
                        verbose_name="Événement",
                    ),
                ),
            ],
            options={
                "verbose_name": "Version de l'appel",
                "verbose_name_plural": "Versions de l'appel",
                "ordering": ["language"],
                "unique_together": {("event", "language")},
            },
        ),
    ]
