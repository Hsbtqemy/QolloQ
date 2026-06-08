from django import forms

from .models import EmailCampaign


class EmailCampaignForm(forms.ModelForm):
    class Meta:
        model = EmailCampaign
        fields = ["subject", "audience", "body"]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 12}),
        }
