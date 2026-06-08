import uuid

from django.db import models

from apps.core.models import BaseModel
from apps.events.models import Event, Membership


class Proposal(BaseModel):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Soumis"
        UNDER_REVIEW = "under_review", "En cours d'évaluation"
        ACCEPTED = "accepted", "Accepté"
        REJECTED = "rejected", "Refusé"

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="proposals",
        verbose_name="Événement",
    )
    title = models.CharField(max_length=500, verbose_name="Titre")
    abstract = models.TextField(verbose_name="Résumé")
    keywords = models.CharField(max_length=255, blank=True, verbose_name="Mots-clés")
    format = models.CharField(max_length=255, blank=True, verbose_name="Format souhaité")
    availability = models.TextField(blank=True, verbose_name="Disponibilités")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
        verbose_name="Statut",
    )

    # Accès sans compte pour le soumissionnaire
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    submitter_email = models.EmailField(verbose_name="Email du soumissionnaire")

    # Assignation manuelle pour évaluation
    assigned_to = models.ManyToManyField(
        Membership,
        blank=True,
        related_name="assigned_proposals",
        verbose_name="Assigné à",
        limit_choices_to={"role__in": [Membership.Role.COMMITTEE, Membership.Role.ORGANIZER]},
    )

    class Meta:
        verbose_name = "Proposition"
        verbose_name_plural = "Propositions"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def is_editable(self):
        return self.status == self.Status.SUBMITTED


class Author(models.Model):
    proposal = models.ForeignKey(
        Proposal,
        on_delete=models.CASCADE,
        related_name="authors",
        verbose_name="Proposition",
    )
    first_name = models.CharField(max_length=150, verbose_name="Prénom")
    last_name = models.CharField(max_length=150, verbose_name="Nom")
    institution = models.CharField(max_length=255, blank=True, verbose_name="Institution")
    email = models.EmailField(blank=True, verbose_name="Email")
    order = models.PositiveSmallIntegerField(default=0, verbose_name="Ordre")

    class Meta:
        verbose_name = "Auteur·ice"
        verbose_name_plural = "Auteur·ices"
        ordering = ["order", "last_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class Evaluation(BaseModel):
    class Verdict(models.TextChoices):
        FOR = "for", "Pour"
        AGAINST = "against", "Contre"
        HESITANT = "hesitant", "Hésitant·e"

    proposal = models.ForeignKey(
        Proposal,
        on_delete=models.CASCADE,
        related_name="evaluations",
        verbose_name="Proposition",
    )
    evaluator = models.ForeignKey(
        Membership,
        on_delete=models.CASCADE,
        related_name="evaluations",
        verbose_name="Évaluateur·ice",
    )
    verdict = models.CharField(
        max_length=10,
        choices=Verdict.choices,
        verbose_name="Avis",
    )
    comment = models.TextField(blank=True, verbose_name="Commentaire")

    class Meta:
        verbose_name = "Évaluation"
        verbose_name_plural = "Évaluations"
        unique_together = [("proposal", "evaluator")]

    def __str__(self):
        return f"{self.evaluator} — {self.proposal} ({self.get_verdict_display()})"
