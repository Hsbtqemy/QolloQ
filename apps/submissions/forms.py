from django import forms
from django.forms import inlineformset_factory

_EMAIL_INPUT_ATTRS = {
    "autocorrect": "off",
    "autocapitalize": "none",
    "spellcheck": "false",
    "inputmode": "email",
}

from apps.events.models import Event

from .models import Author, Evaluation, Proposal, SubmissionField, SubmissionFieldResponse


class PublicProposalForm(forms.ModelForm):
    """Formulaire public de soumission — pas de compte requis."""

    class Meta:
        model = Proposal
        fields = ["title", "abstract", "bio", "keywords", "format", "availability", "submitter_email"]
        widgets = {
            "abstract": forms.Textarea(attrs={"rows": 6}),
            "bio": forms.Textarea(attrs={"rows": 4}),
            "availability": forms.Textarea(attrs={"rows": 3}),
            "submitter_email": forms.EmailInput(attrs=_EMAIL_INPUT_ATTRS),
        }
        labels = {
            "submitter_email": "Votre adresse email (pour recevoir le lien de suivi)",
        }

    def __init__(self, *args, event=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["bio"].required = True
        self._custom_fields = []
        if event is not None:
            if not event.submission_show_keywords:
                self.fields.pop("keywords", None)
            if not event.submission_show_format:
                self.fields.pop("format", None)
            if not event.submission_show_availability:
                self.fields.pop("availability", None)

            self._custom_fields = list(event.submission_fields.order_by("order"))
            existing = {}
            if self.instance and self.instance.pk:
                existing = {
                    r.field_id: r.value
                    for r in self.instance.field_responses.all()
                }
            for cf in self._custom_fields:
                key = f"custom_{cf.pk}"
                field_kwargs = {
                    "label": cf.label,
                    "help_text": cf.help_text,
                    "required": cf.required,
                    "initial": existing.get(cf.pk, ""),
                }
                if cf.kind == SubmissionField.Kind.TEXT:
                    self.fields[key] = forms.CharField(max_length=500, **field_kwargs)
                elif cf.kind == SubmissionField.Kind.TEXTAREA:
                    self.fields[key] = forms.CharField(
                        widget=forms.Textarea(attrs={"rows": 4}), **field_kwargs
                    )
                elif cf.kind == SubmissionField.Kind.CHOICE:
                    choices = [("", "— Choisir —")] + [(o, o) for o in cf.options]
                    self.fields[key] = forms.ChoiceField(choices=choices, **field_kwargs)

    def save_custom_responses(self, proposal):
        for cf in self._custom_fields:
            value = self.cleaned_data.get(f"custom_{cf.pk}", "")
            SubmissionFieldResponse.objects.update_or_create(
                proposal=proposal, field=cf, defaults={"value": value}
            )


class OrganizerProposalForm(forms.ModelForm):
    """Formulaire côté organisateur — respecte la configuration du formulaire de l'événement."""

    class Meta:
        model = Proposal
        fields = ["title", "abstract", "bio", "keywords", "format", "availability", "submitter_email", "status"]
        widgets = {
            "abstract": forms.Textarea(attrs={"rows": 6}),
            "bio": forms.Textarea(attrs={"rows": 4}),
            "availability": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, event=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._custom_fields = []
        if event is not None:
            if not event.submission_show_keywords:
                self.fields.pop("keywords", None)
            if not event.submission_show_format:
                self.fields.pop("format", None)
            if not event.submission_show_availability:
                self.fields.pop("availability", None)

            self._custom_fields = list(event.submission_fields.order_by("order"))
            existing = {}
            if self.instance and self.instance.pk:
                existing = {
                    r.field_id: r.value
                    for r in self.instance.field_responses.all()
                }
            for cf in self._custom_fields:
                key = f"custom_{cf.pk}"
                field_kwargs = {
                    "label": cf.label,
                    "help_text": cf.help_text,
                    "required": cf.required,
                    "initial": existing.get(cf.pk, ""),
                }
                if cf.kind == SubmissionField.Kind.TEXT:
                    self.fields[key] = forms.CharField(max_length=500, **field_kwargs)
                elif cf.kind == SubmissionField.Kind.TEXTAREA:
                    self.fields[key] = forms.CharField(
                        widget=forms.Textarea(attrs={"rows": 4}), **field_kwargs
                    )
                elif cf.kind == SubmissionField.Kind.CHOICE:
                    choices = [("", "— Choisir —")] + [(o, o) for o in cf.options]
                    self.fields[key] = forms.ChoiceField(choices=choices, **field_kwargs)

    def save_custom_responses(self, proposal):
        for cf in self._custom_fields:
            value = self.cleaned_data.get(f"custom_{cf.pk}", "")
            SubmissionFieldResponse.objects.update_or_create(
                proposal=proposal, field=cf, defaults={"value": value}
            )


class AuthorForm(forms.ModelForm):
    class Meta:
        model = Author
        fields = ["first_name", "last_name", "institution", "email"]
        widgets = {
            "email": forms.EmailInput(attrs=_EMAIL_INPUT_ATTRS),
        }


AuthorFormSet = inlineformset_factory(
    Proposal,
    Author,
    form=AuthorForm,
    extra=0,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class EvaluationForm(forms.ModelForm):
    class Meta:
        model = Evaluation
        fields = ["verdict", "comment"]
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 5}),
        }


class ResendTokenForm(forms.Form):
    email = forms.EmailField(
        label="Votre adresse email",
        widget=forms.EmailInput(attrs=_EMAIL_INPUT_ATTRS),
    )


class SubmissionFieldForm(forms.ModelForm):
    options_raw = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Une option par ligne"}),
        label="Options",
        help_text="Une option par ligne. Uniquement pour le type « Choix unique ».",
    )

    class Meta:
        model = SubmissionField
        fields = ["label", "help_text", "kind", "required"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.options:
            self.fields["options_raw"].initial = "\n".join(self.instance.options)

    def save(self, commit=True):
        instance = super().save(commit=False)
        raw = self.cleaned_data.get("options_raw", "")
        instance.options = [line.strip() for line in raw.splitlines() if line.strip()]
        if commit:
            instance.save()
        return instance


class SubmissionInstructionsForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["submission_instructions"]
        widgets = {
            "submission_instructions": forms.Textarea(attrs={"rows": 4}),
        }
        labels = {
            "submission_instructions": "Texte introductif",
        }
        help_texts = {
            "submission_instructions": "Affiché au-dessus du formulaire. Laissez vide si inutile.",
        }
