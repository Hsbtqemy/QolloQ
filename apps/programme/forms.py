from django import forms

from apps.submissions.models import Proposal

from .models import AnnexEvent, Communication, Session


class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ["date", "start_time", "end_time", "location", "title", "moderator"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, event=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._event = event
        self.fields["start_time"].required = False
        self.fields["end_time"].required = False
        if event:
            self.fields["date"].widget.attrs.update({
                "min": str(event.start_date),
                "max": str(event.end_date),
            })

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_time")
        end = cleaned.get("end_time")
        if start and end and end <= start:
            raise forms.ValidationError("L'heure de fin doit être après l'heure de début.")
        if start and not end:
            self.add_error("end_time", "Indiquez l'heure de fin.")
        if end and not start:
            self.add_error("start_time", "Indiquez l'heure de début.")
        if self._event:
            day = cleaned.get("date")
            if day and not (self._event.start_date <= day <= self._event.end_date):
                self.add_error(
                    "date",
                    f"La date doit être comprise entre le {self._event.start_date} et le {self._event.end_date}.",
                )
        return cleaned


class CommunicationForm(forms.ModelForm):
    class Meta:
        model = Communication
        fields = ["kind", "title", "speaker_name", "duration", "proposal"]
        widgets = {
            "proposal": forms.HiddenInput(),
        }

    def __init__(self, *args, event=None, **kwargs):
        super().__init__(*args, **kwargs)
        if event:
            already_used = (
                Communication.objects.filter(session__event=event, proposal__isnull=False)
                .exclude(pk=self.instance.pk if self.instance.pk else None)
                .values_list("proposal_id", flat=True)
            )
            self.fields["proposal"].queryset = Proposal.objects.filter(
                event=event,
                status=Proposal.Status.ACCEPTED,
            ).exclude(pk__in=already_used)


class AnnexEventForm(forms.ModelForm):
    class Meta:
        model = AnnexEvent
        fields = ["date", "start_time", "end_time", "label", "kind", "description"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, event=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._event = event
        if event:
            self.fields["date"].widget.attrs.update({
                "min": str(event.start_date),
                "max": str(event.end_date),
            })

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_time")
        end = cleaned.get("end_time")
        if start and end and end <= start:
            raise forms.ValidationError("L'heure de fin doit être après l'heure de début.")
        if self._event:
            day = cleaned.get("date")
            if day and not (self._event.start_date <= day <= self._event.end_date):
                self.add_error(
                    "date",
                    f"La date doit être comprise entre le {self._event.start_date} et le {self._event.end_date}.",
                )
        return cleaned
