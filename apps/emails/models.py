from django.db import models

from apps.core.models import BaseModel
from apps.events.models import Event


class EmailTemplate(models.Model):
    """Corps éditables des emails transactionnels (sujet + texte FR/EN)."""

    KEY_CHOICES = [
        ("submission_confirmation", "Confirmation de soumission"),
        ("submission_token_reminder", "Renvoi du lien de suivi"),
        ("new_submission_notification", "Notification organisateur — nouvelle soumission"),
        ("member_invitation", "Invitation d'un membre"),
        ("committee_invitation", "Invitation comité scientifique"),
        ("logistics_email_link", "Lien formulaire logistique"),
    ]

    VARIABLES_HELP = {
        "submission_confirmation": [
            ("{{ event_name }}", "Nom de l'événement"),
            ("{{ proposal_title }}", "Titre de la proposition"),
            ("{{ token_url }}", "Lien de suivi — inséré automatiquement après le texte"),
        ],
        "submission_token_reminder": [
            ("{{ event_name }}", "Nom de l'événement"),
            ("{{ proposal_title }}", "Titre de la proposition"),
            ("{{ token_url }}", "Lien de suivi — inséré automatiquement après le texte"),
        ],
        "new_submission_notification": [
            ("{{ event.name }}", "Nom de l'événement"),
            ("{{ proposal.title }}", "Titre de la proposition"),
            ("{{ proposal.submitter_email }}", "Email du soumettant"),
            ("{{ proposal_url }}", "Lien vers la proposition — inséré automatiquement après le texte"),
        ],
        "member_invitation": [
            ("{{ event.name }}", "Nom de l'événement"),
            ("{{ role_label }}", "Rôle (ex. Organisateur)"),
            ("{{ invitation_url }}", "Lien d'invitation — inséré automatiquement après le texte"),
            ("{% if is_new_account %}...{% endif %}", "Contenu conditionnel — nouveau compte"),
        ],
        "committee_invitation": [
            ("{{ membership.first_name }}", "Prénom du membre"),
            ("{{ event.name }}", "Nom de l'événement"),
            ("{{ role_label }}", "Rôle"),
            ("{{ eval_link }}", "Lien d'évaluation — inséré automatiquement après le texte"),
        ],
        "logistics_email_link": [
            ("{{ response.respondent_name }}", "Nom du répondant"),
            ("{{ event.name }}", "Nom de l'événement"),
            ("{{ token_url }}", "Lien du formulaire — inséré automatiquement après le texte"),
        ],
    }

    key = models.CharField(
        max_length=100,
        unique=True,
        choices=KEY_CHOICES,
        verbose_name="Identifiant",
    )
    subject_fr = models.CharField(max_length=500, verbose_name="Objet (FR)")
    subject_en = models.CharField(max_length=500, blank=True, verbose_name="Objet (EN)")
    body_fr = models.TextField(verbose_name="Corps (FR)")
    body_en = models.TextField(blank=True, verbose_name="Corps (EN)")

    class Meta:
        ordering = ["key"]
        verbose_name = "Template email"
        verbose_name_plural = "Templates email"

    def __str__(self):
        return self.get_key_display()

    def variables_help(self):
        return self.VARIABLES_HELP.get(self.key, [])


class EmailCampaign(BaseModel):
    """Campagne email envoyée à un groupe de membres d'un événement."""

    class Audience(models.TextChoices):
        ALL_MEMBERS = "all_members", "Tous les membres"
        SPEAKERS = "speakers", "Intervenants uniquement"
        ACCEPTED = "accepted", "Propositions acceptées (soumettants)"
        COMMITTEE = "committee", "Comité scientifique"

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="email_campaigns",
        verbose_name="Événement",
    )
    subject = models.CharField(max_length=255, verbose_name="Objet")
    body = models.TextField(verbose_name="Corps du message")
    audience = models.CharField(
        max_length=20,
        choices=Audience.choices,
        verbose_name="Destinataires",
    )

    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Envoyé le")
    sent_count = models.PositiveIntegerField(default=0, verbose_name="Nombre envoyé")

    class Meta:
        verbose_name = "Campagne email"
        verbose_name_plural = "Campagnes email"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} — {self.event}"

    @property
    def is_sent(self):
        return self.sent_at is not None
