from django.db import migrations


def create_template(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    EmailTemplate.objects.create(
        key="new_submission_notification",
        subject_fr="Nouvelle soumission — {{ event.name }}",
        subject_en="",
        body_fr=(
            "Bonjour,\n\n"
            "Une nouvelle proposition a été soumise pour {{ event.name }}.\n\n"
            "Titre : {{ proposal.title }}\n"
            "Soumettant : {{ proposal.submitter_email }}\n\n"
            "Utilisez le lien ci-dessous pour la consulter dans votre espace organisateur."
        ),
        body_en="",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("emails", "0002_emailtemplate"),
    ]

    operations = [
        migrations.RunPython(create_template, migrations.RunPython.noop),
    ]
