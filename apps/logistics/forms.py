import json

from django import forms

from .models import BudgetDocument, BudgetLine, BudgetSettings, LogisticsField, LogisticsForm, LogisticsResponse, Reimbursement


class LogisticsFormSettingsForm(forms.ModelForm):
    class Meta:
        model = LogisticsForm
        fields = ["name", "is_open", "deadline", "instructions"]
        widgets = {
            "deadline": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "instructions": forms.Textarea(attrs={"rows": 4}),
        }
        help_texts = {
            "name": "Ex. « Formulaire intervenants pris en charge », « Fiche logistique générale »…",
        }


class LogisticsFieldForm(forms.ModelForm):
    options_text = forms.CharField(
        required=False,
        label="Options (une par ligne)",
        help_text="Pour les types « Choix unique » et « Choix multiple » uniquement.",
        widget=forms.Textarea(attrs={"rows": 4}),
    )

    class Meta:
        model = LogisticsField
        fields = ["label", "help_text", "kind", "required"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.options:
            self.fields["options_text"].initial = "\n".join(self.instance.options)

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("kind")
        options_text = cleaned.get("options_text", "").strip()
        if kind in (LogisticsField.Kind.CHOICE, LogisticsField.Kind.MULTICHOICE):
            if not options_text:
                self.add_error("options_text", "Ce type de champ requiert au moins une option.")
            else:
                cleaned["options"] = [o.strip() for o in options_text.splitlines() if o.strip()]
        else:
            cleaned["options"] = []
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.options = self.cleaned_data.get("options", [])
        if commit:
            instance.save()
        return instance


class LogisticsResponseAdminForm(forms.ModelForm):
    """Création / édition manuelle d'une entrée de réponse par l'organisateur."""

    class Meta:
        model = LogisticsResponse
        fields = ["respondent_name", "respondent_email"]


class ReimbursementForm(forms.ModelForm):
    class Meta:
        model = Reimbursement
        fields = ["person_name", "person_email", "description", "category", "amount", "form_response", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, event=None, **kwargs):
        super().__init__(*args, **kwargs)
        if event is not None:
            self.fields["form_response"].queryset = (
                LogisticsResponse.objects.filter(form__event=event).order_by("respondent_name")
            )
            self.fields["form_response"].label = "Réponse de formulaire liée"
            self.fields["form_response"].required = False
        else:
            self.fields.pop("form_response")


class BudgetSettingsForm(forms.ModelForm):
    class Meta:
        model = BudgetSettings
        fields = ["envelope"]


class BudgetLineForm(forms.ModelForm):
    class Meta:
        model = BudgetLine
        fields = ["label", "category", "amount_planned", "amount_actual", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class BudgetDocumentForm(forms.ModelForm):
    class Meta:
        model = BudgetDocument
        fields = ["label", "kind", "file", "amount"]


def build_response_form(logistics_form, data=None, instance=None):
    """Construit dynamiquement le form de réponse depuis les définitions de champs."""
    fields_qs = logistics_form.fields.order_by("order")

    existing = {}
    if instance and instance.pk:
        for fr in instance.field_responses.select_related("field").all():
            existing[fr.field_id] = fr.value

    form_fields = {}
    for field in fields_qs:
        form_fields[f"field_{field.pk}"] = field.as_form_field()

    DynamicForm = type("DynamicResponseForm", (forms.BaseForm,), {"base_fields": form_fields})
    form = DynamicForm(data=data)

    if existing and data is None:
        for field in fields_qs:
            raw = existing.get(field.pk, "")
            form_key = f"field_{field.pk}"
            if field.kind == LogisticsField.Kind.MULTICHOICE:
                try:
                    form.initial[form_key] = json.loads(raw) if raw else []
                except (ValueError, TypeError):
                    form.initial[form_key] = []
            else:
                form.initial[form_key] = raw

    return form, list(fields_qs)
