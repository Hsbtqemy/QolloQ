from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.core.models import BaseModel


class Event(BaseModel):
    name = models.CharField(max_length=255, verbose_name="Intitulé")
    slug = models.SlugField(max_length=255, unique=True, verbose_name="Identifiant URL")
    description = models.TextField(blank=True, verbose_name="Description")
    call_for_papers = models.TextField(blank=True, verbose_name="Appel à communications")
    bibliography = models.TextField(blank=True, verbose_name="Bibliographie")
    location = models.CharField(max_length=255, blank=True, verbose_name="Lieu")
    start_date = models.DateField(verbose_name="Date de début")
    end_date = models.DateField(verbose_name="Date de fin")

    # Soumissions
    submissions_open = models.BooleanField(default=False, verbose_name="Soumissions ouvertes")
    submission_deadline = models.DateTimeField(
        null=True, blank=True, verbose_name="Date limite de soumission"
    )
    submission_show_keywords = models.BooleanField(
        default=True, verbose_name="Champ « Mots-clés »"
    )
    submission_show_format = models.BooleanField(
        default=True, verbose_name="Champ « Format souhaité »"
    )
    submission_show_availability = models.BooleanField(
        default=False, verbose_name="Champ « Disponibilités »"
    )
    submission_instructions = models.TextField(
        blank=True, verbose_name="Instructions pour les soumissionnaires"
    )

    # Évaluation — options configurables
    class EvalVisibility(models.TextChoices):
        AFTER_OWN = "after_own", "Après dépôt de son propre avis"
        AFTER_DELIBERATION = "after_deliberation", "Après ouverture de la délibération"

    class EvalAssignment(models.TextChoices):
        ALL = "all", "Tout le comité évalue toutes les propositions"
        MANUAL = "manual", "Assignation manuelle par l'organisateur"

    eval_visibility = models.CharField(
        max_length=30,
        choices=EvalVisibility.choices,
        default=EvalVisibility.AFTER_OWN,
        verbose_name="Visibilité des avis",
    )
    eval_anonymous = models.BooleanField(
        default=False,
        verbose_name="Anonymat entre évaluateurs",
        help_text="Les évaluateurs ne voient pas le nom des autres membres du comité.",
    )
    eval_assignment = models.CharField(
        max_length=10,
        choices=EvalAssignment.choices,
        default=EvalAssignment.ALL,
        verbose_name="Mode d'assignation",
    )
    double_blind = models.BooleanField(
        default=False,
        verbose_name="Double-aveugle",
        help_text="Les noms des auteurs sont masqués aux évaluateurs.",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_events",
        verbose_name="Créé par",
    )

    class Meta:
        verbose_name = "Événement"
        verbose_name_plural = "Événements"
        ordering = ["-start_date"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "evenement"
            slug = base
            n = 1
            while Event.objects.filter(slug=slug).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Membership(BaseModel):
    class Role(models.TextChoices):
        ORGANIZER = "organizer", "Organisateur·ice"
        COMMITTEE = "committee", "Comité scientifique"
        SPEAKER = "speaker", "Intervenant·e"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="Utilisateur·ice",
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="Événement",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.ORGANIZER,
        verbose_name="Rôle",
    )

    class Meta:
        verbose_name = "Membre"
        verbose_name_plural = "Membres"
        unique_together = [("user", "event")]

    def __str__(self):
        return f"{self.user} — {self.event} ({self.get_role_display()})"

    @property
    def is_organizer(self):
        return self.role == self.Role.ORGANIZER

    @property
    def is_committee(self):
        return self.role in (self.Role.ORGANIZER, self.Role.COMMITTEE)
