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
        CANCELLED = "cancelled", "Annulé·e"

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="proposals",
        verbose_name="Événement",
    )
    title = models.CharField(max_length=500, verbose_name="Titre de la communication")
    abstract = models.TextField(verbose_name="Proposition de communication")
    bio = models.TextField(blank=True, verbose_name="Bio-bibliographie")
    keywords = models.CharField(max_length=255, blank=True, verbose_name="Mots-clés")
    format = models.CharField(max_length=255, blank=True, verbose_name="Format souhaité")
    availability = models.TextField(blank=True, verbose_name="Disponibilités")
    class Attendance(models.TextChoices):
        PENDING   = "pending",   "En attente"
        CONFIRMED = "confirmed", "Confirmé·e"
        CANCELLED = "cancelled", "Annulé·e"

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
        verbose_name="Statut",
    )
    attendance = models.CharField(
        max_length=20,
        choices=Attendance.choices,
        default=Attendance.PENDING,
        verbose_name="Présence",
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


class SubmissionField(models.Model):
    class Kind(models.TextChoices):
        TEXT = "text", "Texte court"
        TEXTAREA = "textarea", "Texte long"
        CHOICE = "choice", "Choix unique"

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="submission_fields",
        verbose_name="Événement",
    )
    label = models.CharField(max_length=255, verbose_name="Intitulé")
    label_en = models.CharField(max_length=255, blank=True, verbose_name="Intitulé (EN)")
    help_text = models.CharField(max_length=500, blank=True, verbose_name="Texte d'aide")
    help_text_en = models.CharField(max_length=500, blank=True, verbose_name="Texte d'aide (EN)")
    kind = models.CharField(max_length=20, choices=Kind.choices, verbose_name="Type")
    options = models.JSONField(default=list, blank=True, verbose_name="Options")
    required = models.BooleanField(default=False, verbose_name="Obligatoire")
    order = models.PositiveSmallIntegerField(default=0, verbose_name="Ordre")

    class Meta:
        verbose_name = "Champ de soumission"
        verbose_name_plural = "Champs de soumission"
        ordering = ["order"]

    def __str__(self):
        return f"{self.label} ({self.get_kind_display()})"


class SubmissionFieldResponse(models.Model):
    proposal = models.ForeignKey(
        Proposal,
        on_delete=models.CASCADE,
        related_name="field_responses",
        verbose_name="Proposition",
    )
    field = models.ForeignKey(
        SubmissionField,
        on_delete=models.CASCADE,
        related_name="responses",
        verbose_name="Champ",
    )
    value = models.TextField(blank=True, verbose_name="Valeur")

    class Meta:
        verbose_name = "Réponse champ"
        verbose_name_plural = "Réponses champs"
        unique_together = [("proposal", "field")]

    def __str__(self):
        return f"{self.field.label} : {self.value[:50]}"


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
