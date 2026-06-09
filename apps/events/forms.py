from django import forms
from django.contrib.auth import get_user_model

from .models import Event, Membership


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "name", "description", "location", "start_date", "end_date",
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
        fields = ["banner", "primary_color", "tagline", "site_footer", "call_for_papers", "bibliography"]
        widgets = {
            "call_for_papers": forms.Textarea(attrs={"rows": 12}),
            "bibliography": forms.Textarea(attrs={"rows": 6}),
            "banner": forms.ClearableFileInput(attrs={"accept": "image/*"}),
            "tagline": forms.TextInput(),
            "site_footer": forms.TextInput(),
        }
        help_texts = {
            "call_for_papers": "Affiché sur la page publique et dans le PDF téléchargeable.",
            "bibliography": "Références bibliographiques — optionnel.",
        }


class MemberAddForm(forms.Form):
    email = forms.EmailField(
        label="Adresse email",
        widget=forms.EmailInput(attrs={
            "autocorrect": "off",
            "autocapitalize": "none",
            "spellcheck": "false",
            "inputmode": "email",
        }),
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

    def clean_email(self):
        email = self.cleaned_data["email"]
        User = get_user_model()
        try:
            self.cleaned_user = User.objects.get(email=email)
            self.is_new_user = False
        except User.DoesNotExist:
            self.is_new_user = True
        if not self.is_new_user and self._event:
            if Membership.objects.filter(user=self.cleaned_user, event=self._event).exists():
                raise forms.ValidationError("Cette personne est déjà membre de l'événement.")
        return email
