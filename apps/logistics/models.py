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
    name_en = models.CharField(max_length=255, blank=True, verbose_name="Nom du formulaire (EN)")
    is_open = models.BooleanField(default=False, verbose_name="Ouvert aux réponses")
    deadline = models.DateTimeField(null=True, blank=True, verbose_name="Date limite de réponse")
    instructions = models.TextField(blank=True, verbose_name="Instructions")
    instructions_en = models.TextField(blank=True, verbose_name="Instructions (EN)")

    class Meta:
        verbose_name = "Formulaire logistique"
        verbose_name_plural = "Formulaires logistiques"

    def __str__(self):
        return f"{self.name} — {self.event}"


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
    label_en = models.CharField(max_length=255, blank=True, verbose_name="Intitulé (EN)")
    help_text = models.CharField(max_length=500, blank=True, verbose_name="Texte d'aide")
    help_text_en = models.CharField(max_length=500, blank=True, verbose_name="Texte d'aide (EN)")
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

    def as_form_field(self, lang='fr'):
        """Retourne le champ Django Forms correspondant à ce champ logistique."""
        kwargs = {
            "label": (self.label_en if lang == 'en' and self.label_en else self.label),
            "help_text": (self.help_text_en if lang == 'en' and self.help_text_en else self.help_text),
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
                widget=django_forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"), **kwargs
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


class BudgetCharge(BaseModel):
    """Prise en charge individuelle rattachée à un poste budgétaire."""

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        SENT = "sent", "Envoyé"
        RECEIVED = "received", "Reçu"

    budget_line = models.ForeignKey(
        "BudgetLine",
        on_delete=models.CASCADE,
        related_name="charges",
        verbose_name="Poste budgétaire",
    )
    person_name = models.CharField(max_length=255, verbose_name="Nom")
    person_email = models.EmailField(blank=True, verbose_name="Email")
    description = models.CharField(max_length=500, verbose_name="Description")
    amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name="Montant (€)",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Statut",
    )
    form_response = models.ForeignKey(
        LogisticsResponse,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="charges",
        verbose_name="Réponse liée",
    )
    notes = models.TextField(blank=True, verbose_name="Notes")

    class Meta:
        verbose_name = "Prise en charge"
        verbose_name_plural = "Prises en charge"
        ordering = ["person_name"]

    def __str__(self):
        return f"{self.person_name} — {self.description} ({self.amount} €)"


class BudgetSettings(models.Model):
    """Paramètres budget d'un événement (enveloppe globale)."""

    event = models.OneToOneField(
        Event,
        on_delete=models.CASCADE,
        related_name="budget_settings",
        verbose_name="Événement",
    )
    envelope = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Enveloppe totale (€)",
        help_text="Budget global alloué à l'événement.",
    )

    class Meta:
        verbose_name = "Paramètres budget"
        verbose_name_plural = "Paramètres budget"

    def __str__(self):
        return f"Budget — {self.event}"


class BudgetLine(BaseModel):
    """Poste budgétaire d'un événement."""

    class Category(models.TextChoices):
        VENUE = "salle", "Salle"
        CATERING = "traiteur", "Traiteur"
        RESTAURANT = "restaurant", "Restaurant"
        DRINKS = "boissons", "Boissons"
        COFFEE = "cafe", "Pauses café"
        TRANSPORT = "transport", "Transport"
        COMMUNICATION = "communication", "Communication"
        OTHER = "autre", "Autre"

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="budget_lines",
        verbose_name="Événement",
    )
    label = models.CharField(max_length=255, verbose_name="Intitulé")
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        verbose_name="Catégorie",
    )
    amount_planned = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Montant prévu (€)"
    )
    amount_actual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Montant réel (€)",
    )
    notes = models.TextField(blank=True, verbose_name="Notes")

    class Meta:
        verbose_name = "Poste budgétaire"
        verbose_name_plural = "Postes budgétaires"
        ordering = ["category", "label"]

    def __str__(self):
        return f"{self.label} ({self.get_category_display()}) — {self.event}"


class BudgetDocument(models.Model):
    """Devis ou facture attaché à un poste budgétaire."""

    class Kind(models.TextChoices):
        QUOTE = "devis", "Devis"
        INVOICE = "facture", "Facture"
        PURCHASE_ORDER = "bon_de_commande", "Bon de commande"

    line = models.ForeignKey(
        BudgetLine,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name="Poste",
    )
    label = models.CharField(max_length=255, verbose_name="Intitulé")
    kind = models.CharField(max_length=20, choices=Kind.choices, verbose_name="Type")
    file = models.FileField(upload_to="budget/", verbose_name="Fichier")
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Montant (€)"
    )

    class Meta:
        verbose_name = "Document budgétaire"
        verbose_name_plural = "Documents budgétaires"

    def __str__(self):
        return f"{self.label} ({self.get_kind_display()})"
