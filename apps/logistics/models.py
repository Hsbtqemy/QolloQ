import json
import uuid

from django import forms as django_forms
from django.db import models

from apps.core.models import BaseModel
from apps.events.models import Event


class LogisticsForm(BaseModel):
    """Un formulaire organisationnel configurable pour un événement."""

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="logistics_forms",
        verbose_name="Événement",
    )
    name = models.CharField(max_length=255, default="Formulaire logistique", verbose_name="Nom du formulaire")
    is_open = models.BooleanField(default=False, verbose_name="Ouvert aux réponses")
    deadline = models.DateTimeField(null=True, blank=True, verbose_name="Date limite de réponse")
    instructions = models.TextField(blank=True, verbose_name="Instructions")

    class Meta:
        verbose_name = "Formulaire logistique"
        verbose_name_plural = "Formulaires logistiques"

    def __str__(self):
        return f"Formulaire logistique — {self.event}"


class LogisticsField(models.Model):
    """Un champ configurable du formulaire logistique."""

    class Kind(models.TextChoices):
        TEXT = "text", "Texte court"
        TEXTAREA = "textarea", "Texte long"
        BOOLEAN = "boolean", "Oui / Non"
        CHOICE = "choice", "Choix unique"
        MULTICHOICE = "multichoice", "Choix multiple"
        DATE = "date", "Date"
        TIME = "time", "Heure"

    form = models.ForeignKey(
        LogisticsForm,
        on_delete=models.CASCADE,
        related_name="fields",
        verbose_name="Formulaire",
    )
    label = models.CharField(max_length=255, verbose_name="Intitulé")
    help_text = models.CharField(max_length=500, blank=True, verbose_name="Texte d'aide")
    kind = models.CharField(max_length=20, choices=Kind.choices, verbose_name="Type")
    options = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Options",
        help_text="Pour les types choix : liste des options, une par ligne.",
    )
    required = models.BooleanField(default=False, verbose_name="Obligatoire")
    order = models.PositiveSmallIntegerField(default=0, verbose_name="Ordre")

    class Meta:
        verbose_name = "Champ"
        verbose_name_plural = "Champs"
        ordering = ["order"]

    def __str__(self):
        return f"{self.label} ({self.get_kind_display()})"

    def as_form_field(self):
        """Retourne le champ Django Forms correspondant à ce champ logistique."""
        kwargs = {
            "label": self.label,
            "help_text": self.help_text,
            "required": self.required,
        }
        if self.kind == self.Kind.TEXT:
            return django_forms.CharField(max_length=500, **kwargs)
        if self.kind == self.Kind.TEXTAREA:
            return django_forms.CharField(
                widget=django_forms.Textarea(attrs={"rows": 4}), **kwargs
            )
        if self.kind == self.Kind.BOOLEAN:
            kwargs["required"] = False
            return django_forms.BooleanField(**kwargs)
        if self.kind == self.Kind.CHOICE:
            choices = [("", "— Choisir —")] + [(o, o) for o in self.options]
            return django_forms.ChoiceField(choices=choices, **kwargs)
        if self.kind == self.Kind.MULTICHOICE:
            choices = [(o, o) for o in self.options]
            return django_forms.MultipleChoiceField(
                widget=django_forms.CheckboxSelectMultiple,
                choices=choices,
                **kwargs,
            )
        if self.kind == self.Kind.DATE:
            return django_forms.DateField(
                widget=django_forms.DateInput(attrs={"type": "date"}), **kwargs
            )
        if self.kind == self.Kind.TIME:
            return django_forms.TimeField(
                widget=django_forms.TimeInput(attrs={"type": "time"}), **kwargs
            )
        return django_forms.CharField(**kwargs)


class LogisticsResponse(BaseModel):
    """Réponse d'un intervenant au formulaire logistique."""

    form = models.ForeignKey(
        LogisticsForm,
        on_delete=models.CASCADE,
        related_name="responses",
        verbose_name="Formulaire",
    )
    respondent_name = models.CharField(max_length=255, verbose_name="Nom de l'intervenant·e")
    respondent_email = models.EmailField(verbose_name="Email")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_complete = models.BooleanField(default=False, verbose_name="Réponse complète")

    class Meta:
        verbose_name = "Réponse logistique"
        verbose_name_plural = "Réponses logistiques"
        ordering = ["respondent_name"]

    def __str__(self):
        return f"{self.respondent_name} — {self.form.event}"


class LogisticsFieldResponse(models.Model):
    """Valeur d'un champ individuel dans une réponse logistique."""

    response = models.ForeignKey(
        LogisticsResponse,
        on_delete=models.CASCADE,
        related_name="field_responses",
        verbose_name="Réponse",
    )
    field = models.ForeignKey(
        LogisticsField,
        on_delete=models.CASCADE,
        related_name="field_responses",
        verbose_name="Champ",
    )
    value = models.TextField(blank=True, verbose_name="Valeur")

    class Meta:
        verbose_name = "Valeur de champ"
        verbose_name_plural = "Valeurs de champs"
        unique_together = [("response", "field")]

    def __str__(self):
        return f"{self.field.label} : {self.value[:50]}"

    @property
    def display_value(self):
        """Valeur lisible — désérialise JSON pour multichoix, traduit oui/non pour booléens."""
        if self.field.kind == LogisticsField.Kind.MULTICHOICE:
            try:
                items = json.loads(self.value)
                return ", ".join(items) if items else "—"
            except (ValueError, TypeError):
                return self.value or "—"
        if self.field.kind == LogisticsField.Kind.BOOLEAN:
            return "Oui" if self.value == "true" else "Non"
        return self.value or "—"
