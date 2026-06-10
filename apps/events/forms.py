import re

from django import forms
from django.contrib.auth import get_user_model

from .models import CallVersion, Event, Membership


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "name", "description", "location", "start_date", "end_date",
            "is_bilingual", "from_name",
            "submissions_open", "submission_deadline",
            "eval_visibility", "eval_anonymous", "eval_assignment", "double_blind",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "submission_deadline": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and end < start:
            self.add_error("end_date", "La date de fin doit être égale ou postérieure à la date de début.")
        return cleaned


class EventPublicPageForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["banner", "primary_color", "tagline", "tagline_en", "site_footer", "site_footer_en"]
        widgets = {
            "banner": forms.ClearableFileInput(attrs={"accept": "image/*"}),
            "tagline": forms.TextInput(),
            "tagline_en": forms.TextInput(),
            "site_footer": forms.TextInput(),
            "site_footer_en": forms.TextInput(),
        }

    def clean_primary_color(self):
        color = self.cleaned_data.get("primary_color", "").strip()
        if color and not re.match(r'^#[0-9a-fA-F]{6}$', color):
            raise forms.ValidationError("Format invalide. Utilisez un code hexadécimal à 6 chiffres, ex. #1e3a5f.")
        return color


class CallVersionForm(forms.ModelForm):
    class Meta:
        model = CallVersion
        fields = ["language", "content", "bibliography"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 12}),
            "bibliography": forms.Textarea(attrs={"rows": 6}),
        }
        help_texts = {
            "content": (
                "Affiché sur la page publique et dans le PDF. "
                "Mise en forme Markdown acceptée. "
                "Notes de bas de page : écrire [^1] dans le texte, puis [^1]: texte de la note à la fin."
            ),
            "bibliography": "Références bibliographiques — optionnel. Markdown accepté.",
        }


class MemberAddForm(forms.Form):
    _EMAIL_ATTRS = {
        "autocorrect": "off",
        "autocapitalize": "none",
        "spellcheck": "false",
        "inputmode": "email",
    }

    email = forms.EmailField(
        label="Adresse email",
        widget=forms.EmailInput(attrs=_EMAIL_ATTRS),
    )
    first_name = forms.CharField(max_length=150, required=False, label="Prénom")
    last_name = forms.CharField(max_length=150, required=False, label="Nom")
    role = forms.ChoiceField(
        choices=[
            (Membership.Role.ORGANIZER, "Organisateur·ice"),
            (Membership.Role.COMMITTEE, "Comité scientifique"),
            (Membership.Role.SPEAKER, "Intervenant·e"),
        ],
        label="Rôle",
    )

    def __init__(self, *args, event=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._event = event
        self.cleaned_user = None
        self.is_new_user = False

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email")
        role = cleaned.get("role")
        if not email or not role:
            return cleaned

        User = get_user_model()
        if role == Membership.Role.ORGANIZER:
            try:
                self.cleaned_user = User.objects.get(email=email)
                self.is_new_user = False
            except User.DoesNotExist:
                self.is_new_user = True
            if not self.is_new_user and self._event:
                if Membership.objects.filter(user=self.cleaned_user, event=self._event).exists():
                    self.add_error("email", "Cette personne est déjà membre de l'événement.")
        else:
            # Comité / intervenant — pas de compte. Vérification par email.
            if not cleaned.get("first_name") or not cleaned.get("last_name"):
                raise forms.ValidationError("Le prénom et le nom sont obligatoires pour le comité et les intervenants.")
            if self._event:
                # Doublon via compte existant
                try:
                    existing_user = User.objects.get(email=email)
                    if Membership.objects.filter(user=existing_user, event=self._event).exists():
                        self.add_error("email", "Cette personne est déjà membre de l'événement.")
                except User.DoesNotExist:
                    pass
                # Doublon via membership sans compte
                if Membership.objects.filter(email=email, event=self._event).exists():
                    self.add_error("email", "Cette adresse email est déjà enregistrée pour cet événement.")

        return cleaned
