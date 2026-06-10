from django.db import migrations, models


INITIAL_TEMPLATES = [
    {
        "key": "submission_confirmation",
        "subject_fr": "Proposition reçue — {{ event_name }}",
        "subject_en": "Proposal received — {{ event_name }}",
        "body_fr": (
            "Bonjour,\n\n"
            "Nous avons bien reçu votre proposition pour {{ event_name }}.\n\n"
            "Titre : {{ proposal_title }}\n\n"
            "Vous pouvez suivre l'avancement de votre dossier ou apporter des modifications "
            "via votre lien personnel. Conservez-le précieusement — il vous permettra d'accéder "
            "à votre soumission sans créer de compte.\n\n"
            "Vous recevrez un message dès qu'une décision sera prise concernant votre proposition.\n\n"
            "Cordialement,\n"
            "L'équipe organisatrice"
        ),
        "body_en": (
            "Hello,\n\n"
            "We have received your proposal for {{ event_name }}.\n\n"
            "Title: {{ proposal_title }}\n\n"
            "You can track the progress of your submission or make changes via your personal link. "
            "Please keep it safe — it allows you to access your submission without creating an account.\n\n"
            "You will receive a message once a decision has been made regarding your proposal.\n\n"
            "Best regards,\n"
            "The organising committee"
        ),
    },
    {
        "key": "submission_token_reminder",
        "subject_fr": "Votre lien de suivi — {{ event_name }}",
        "subject_en": "Your access link — {{ event_name }}",
        "body_fr": (
            "Bonjour,\n\n"
            "Vous avez demandé à retrouver le lien d'accès à votre soumission "
            "pour {{ event_name }}.\n\n"
            "Titre : {{ proposal_title }}\n\n"
            "Si vous n'êtes pas à l'origine de cette demande, ignorez simplement ce message.\n\n"
            "Cordialement,\n"
            "L'équipe organisatrice"
        ),
        "body_en": (
            "Hello,\n\n"
            "You requested to retrieve the access link to your submission "
            "for {{ event_name }}.\n\n"
            "Title: {{ proposal_title }}\n\n"
            "If you did not make this request, please ignore this message.\n\n"
            "Best regards,\n"
            "The organising committee"
        ),
    },
    {
        "key": "member_invitation",
        "subject_fr": "Invitation — {{ event.name }}",
        "subject_en": "Invitation — {{ event.name }}",
        "body_fr": (
            "Bonjour,\n\n"
            "Vous avez été invité·e à rejoindre l'événement « {{ event.name }} » "
            "en tant que {{ role_label }}.\n\n"
            "{% if is_new_account %}Un compte QolloQ a été créé pour vous avec cette adresse email. "
            "Cliquez sur le lien ci-dessous pour définir votre mot de passe et accéder à l'application."
            "{% else %}Cliquez sur le lien ci-dessous pour vous connecter et accéder à l'événement.{% endif %}\n\n"
            "{{ event.name }}"
        ),
        "body_en": (
            "Hello,\n\n"
            "You have been invited to join the event « {{ event.name }} » "
            "as {{ role_label }}.\n\n"
            "{% if is_new_account %}A QolloQ account has been created for you with this email address. "
            "Click the link below to set your password and access the application."
            "{% else %}Click the link below to log in and access the event.{% endif %}\n\n"
            "{{ event.name }}"
        ),
    },
    {
        "key": "committee_invitation",
        "subject_fr": "Invitation à évaluer — {{ event.name }}",
        "subject_en": "Invitation to review — {{ event.name }}",
        "body_fr": (
            "Bonjour {{ membership.first_name }},\n\n"
            "Vous avez été invité·e à participer à l'évaluation des propositions soumises "
            "à « {{ event.name }} » en tant que {{ role_label }}.\n\n"
            "Cliquez sur le lien ci-dessous pour accéder aux propositions à évaluer. "
            "Ce lien est personnel — gardez-le précieusement, il vous permettra de retrouver "
            "vos évaluations à tout moment.\n\n"
            "{{ event.name }}"
        ),
        "body_en": (
            "Hello {{ membership.first_name }},\n\n"
            "You have been invited to review the proposals submitted to « {{ event.name }} » "
            "as {{ role_label }}.\n\n"
            "Click the link below to access the proposals to review. "
            "This link is personal — please keep it safe, it will allow you to retrieve "
            "your reviews at any time.\n\n"
            "{{ event.name }}"
        ),
    },
    {
        "key": "logistics_email_link",
        "subject_fr": "Formulaire logistique — {{ event.name }}",
        "subject_en": "Logistics form — {{ event.name }}",
        "body_fr": (
            "Bonjour {{ response.respondent_name }},\n\n"
            "Vous êtes invité·e à remplir le formulaire logistique "
            "de l'événement « {{ event.name }} ».\n\n"
            "Ce lien vous est personnel. Vous pouvez revenir le compléter à tout moment.\n\n"
            "Cordialement,\n"
            "L'équipe d'organisation — {{ event.name }}"
        ),
        "body_en": (
            "Hello {{ response.respondent_name }},\n\n"
            "You are invited to fill in the logistics form "
            "for the event « {{ event.name }} ».\n\n"
            "This link is personal. You can come back to complete it at any time.\n\n"
            "Best regards,\n"
            "The organising committee — {{ event.name }}"
        ),
    },
]


def create_initial_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    for data in INITIAL_TEMPLATES:
        EmailTemplate.objects.create(**data)


class Migration(migrations.Migration):

    dependencies = [
        ("emails", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmailTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(
                    choices=[
                        ("submission_confirmation", "Confirmation de soumission"),
                        ("submission_token_reminder", "Renvoi du lien de suivi"),
                        ("member_invitation", "Invitation d'un membre"),
                        ("committee_invitation", "Invitation comité scientifique"),
                        ("logistics_email_link", "Lien formulaire logistique"),
                    ],
                    max_length=100,
                    unique=True,
                    verbose_name="Identifiant",
                )),
                ("subject_fr", models.CharField(max_length=500, verbose_name="Objet (FR)")),
                ("subject_en", models.CharField(blank=True, max_length=500, verbose_name="Objet (EN)")),
                ("body_fr", models.TextField(verbose_name="Corps (FR)")),
                ("body_en", models.TextField(blank=True, verbose_name="Corps (EN)")),
            ],
            options={
                "verbose_name": "Template email",
                "verbose_name_plural": "Templates email",
                "ordering": ["key"],
            },
        ),
        migrations.RunPython(create_initial_templates, migrations.RunPython.noop),
    ]
