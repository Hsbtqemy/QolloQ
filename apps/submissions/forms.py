from django import forms
from django.forms import inlineformset_factory

from .models import Author, Evaluation, Proposal


class PublicProposalForm(forms.ModelForm):
    """Formulaire public de soumission — pas de compte requis."""

    class Meta:
        model = Proposal
        fields = ["title", "abstract", "keywords", "format", "availability", "submitter_email"]
        widgets = {
            "abstract": forms.Textarea(attrs={"rows": 6}),
            "availability": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "submitter_email": "Votre adresse email (pour recevoir le lien de suivi)",
        }


class OrganizerProposalForm(forms.ModelForm):
    """Formulaire côté organisateur — peut modifier n'importe quelle proposition."""

    class Meta:
        model = Proposal
        fields = ["title", "abstract", "keywords", "format", "availability", "submitter_email", "status"]
        widgets = {
            "abstract": forms.Textarea(attrs={"rows": 6}),
            "availability": forms.Textarea(attrs={"rows": 3}),
        }


class AuthorForm(forms.ModelForm):
    class Meta:
        model = Author
        fields = ["first_name", "last_name", "institution", "email"]


AuthorFormSet = inlineformset_factory(
    Proposal,
    Author,
    form=AuthorForm,
    extra=1,
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
    email = forms.EmailField(label="Votre adresse email")
