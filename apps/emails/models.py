from django.db import models

from apps.core.models import BaseModel
from apps.events.models import Event


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
