import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.core.models import BaseModel


class Event(BaseModel):
    name = models.CharField(max_length=255, verbose_name="Intitulé")
    slug = models.SlugField(max_length=255, unique=True, verbose_name="Identifiant URL")
    description = models.TextField(blank=True, verbose_name="Description")
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
    submission_instructions_en = models.TextField(
        blank=True, verbose_name="Instructions pour les soumissionnaires (EN)"
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

    # Bilingue
    is_bilingual = models.BooleanField(
        default=False,
        verbose_name="Événement bilingue (FR/EN)",
        help_text="Active les champs anglais et le sélecteur de langue sur les pages publiques.",
    )

    # Emails
    from_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Nom d'expéditeur",
        help_text="Affiché dans la boîte de réception à la place du nom de l'événement. Ex. : « Jean Dupont — Colloque 2026 ».",
    )

    banner = models.ImageField(
        upload_to="events/banners/",
        blank=True,
        null=True,
        verbose_name="Visuel",
        help_text="Affiché en haut de la page publique. Recommandé : 1200 × 400 px.",
    )

    # Personnalisation du site public
    primary_color = models.CharField(
        max_length=7,
        blank=True,
        verbose_name="Couleur principale",
        help_text="Code hexadécimal, ex. #1e3a5f. Laisser vide pour la couleur par défaut.",
    )
    tagline = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Sous-titre",
        help_text="Court texte affiché sous le nom de l'événement sur la page publique.",
    )
    tagline_en = models.CharField(max_length=200, blank=True, verbose_name="Sous-titre (EN)")
    site_footer = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Pied de page",
        help_text="Texte affiché en bas de chaque page. Ex. : « Organisé par l'Univ. de Lyon ».",
    )
    site_footer_en = models.CharField(max_length=200, blank=True, verbose_name="Pied de page (EN)")

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


class KeyDate(BaseModel):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="key_dates")
    label = models.CharField(max_length=150, verbose_name="Intitulé")
    date  = models.DateField(verbose_name="Date")

    class Meta:
        ordering = ["date"]
        verbose_name = "Date clé"
        verbose_name_plural = "Dates clés"

    def __str__(self):
        return f"{self.label} ({self.date})"


class Task(BaseModel):
    event    = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="tasks")
    title    = models.CharField(max_length=200, verbose_name="Tâche")
    done     = models.BooleanField(default=False, verbose_name="Terminée")
    due_date = models.DateField(null=True, blank=True, verbose_name="Échéance")
    order    = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "due_date", "created_at"]
        verbose_name = "Tâche"
        verbose_name_plural = "Tâches"

    def __str__(self):
        return self.title


class CallVersion(BaseModel):
    class Language(models.TextChoices):
        FR = "fr", "Français"
        EN = "en", "English"
        DE = "de", "Deutsch"
        ES = "es", "Español"
        IT = "it", "Italiano"
        PT = "pt", "Português"

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="call_versions",
        verbose_name="Événement",
    )
    language = models.CharField(
        max_length=5,
        choices=Language.choices,
        verbose_name="Langue",
    )
    content = models.TextField(blank=True, verbose_name="Appel à communications")
    bibliography = models.TextField(blank=True, verbose_name="Bibliographie")

    class Meta:
        unique_together = [("event", "language")]
        ordering = ["language"]
        verbose_name = "Version de l'appel"
        verbose_name_plural = "Versions de l'appel"

    def __str__(self):
        return f"{self.get_language_display()} — {self.event.name}"


class Membership(BaseModel):
    class Role(models.TextChoices):
        ORGANIZER = "organizer", "Organisateur·ice"
        COMMITTEE = "committee", "Comité scientifique"
        SPEAKER = "speaker", "Intervenant·e"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
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

    # Champs pour les membres sans compte (comité, intervenants)
    first_name = models.CharField(max_length=150, blank=True, verbose_name="Prénom")
    last_name = models.CharField(max_length=150, blank=True, verbose_name="Nom")
    email = models.EmailField(blank=True, verbose_name="Email")
    eval_token = models.UUIDField(null=True, unique=True, editable=False, verbose_name="Token d'évaluation")

    class Meta:
        verbose_name = "Membre"
        verbose_name_plural = "Membres"
        unique_together = [("user", "event")]

    def __str__(self):
        return f"{self.display_name} — {self.event} ({self.get_role_display()})"

    @property
    def display_name(self):
        if self.user_id:
            return self.user.get_full_name() or self.user.email
        return f"{self.first_name} {self.last_name}".strip() or self.email

    @property
    def contact_email(self):
        return self.user.email if self.user_id else self.email

    @property
    def is_organizer(self):
        return self.role == self.Role.ORGANIZER

    @property
    def is_committee(self):
        return self.role in (self.Role.ORGANIZER, self.Role.COMMITTEE)
