from django import forms

from apps.core.utils import validate_file_size

from .models import EventDocument


class EventDocumentForm(forms.ModelForm):
    class Meta:
        model = EventDocument
        fields = ["name", "description", "file"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_file(self):
        file = self.cleaned_data.get("file")
        if file:
            validate_file_size(file)
        return file
