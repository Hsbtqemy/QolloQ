import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def populate_eval_tokens(apps, schema_editor):
    Membership = apps.get_model("events", "Membership")
    for membership in Membership.objects.filter(eval_token__isnull=True):
        membership.eval_token = uuid.uuid4()
        membership.save(update_fields=["eval_token"])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("events", "0009_migrate_call_data"),
    ]

    operations = [
        migrations.AddField(
            model_name="membership",
            name="first_name",
            field=models.CharField(blank=True, max_length=150, verbose_name="Prénom"),
        ),
        migrations.AddField(
            model_name="membership",
            name="last_name",
            field=models.CharField(blank=True, max_length=150, verbose_name="Nom"),
        ),
        migrations.AddField(
            model_name="membership",
            name="email",
            field=models.EmailField(blank=True, verbose_name="Email"),
        ),
        migrations.AddField(
            model_name="membership",
            name="eval_token",
            field=models.UUIDField(null=True, editable=False, verbose_name="Token d'évaluation"),
        ),
        migrations.AlterField(
            model_name="membership",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="memberships",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Utilisateur·ice",
            ),
        ),
        migrations.RunPython(populate_eval_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="membership",
            name="eval_token",
            field=models.UUIDField(
                null=True, unique=True, editable=False, verbose_name="Token d'évaluation"
            ),
        ),
    ]
