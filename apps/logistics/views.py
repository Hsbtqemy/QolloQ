import json

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.core.mixins import CommitteeRequiredMixin, OrganizerRequiredMixin

from .forms import (
    LogisticsFieldForm,
    LogisticsFormSettingsForm,
    LogisticsResponseAdminForm,
    build_response_form,
)
from .mail import send_logistics_link
from .models import (
    LogisticsField,
    LogisticsFieldResponse,
    LogisticsForm,
    LogisticsResponse,
)


def _get_or_create_logistics_form(event):
    form, _ = LogisticsForm.objects.get_or_create(event=event)
    return form


# ---------------------------------------------------------------------------
# Organizer: configure the logistics form
# ---------------------------------------------------------------------------


class LogisticsSettingsView(OrganizerRequiredMixin, View):
    def get(self, request, event_slug):
        lf = _get_or_create_logistics_form(self.event)
        form = LogisticsFormSettingsForm(instance=lf)
        fields = lf.fields.order_by("order")
        return render(
            request,
            "logistics/settings.html",
            {"event": self.event, "logistics_form": lf, "form": form, "fields": fields},
        )

    def post(self, request, event_slug):
        lf = _get_or_create_logistics_form(self.event)
        form = LogisticsFormSettingsForm(request.POST, instance=lf)
        if form.is_valid():
            form.save()
            messages.success(request, "Paramètres enregistrés.")
            return redirect("logistics:settings", event_slug=event_slug)
        fields = lf.fields.order_by("order")
        return render(
            request,
            "logistics/settings.html",
            {"event": self.event, "logistics_form": lf, "form": form, "fields": fields},
        )


class FieldCreateView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug):
        lf = _get_or_create_logistics_form(self.event)
        form = LogisticsFieldForm(request.POST)
        if form.is_valid():
            field = form.save(commit=False)
            field.form = lf
            field.order = (lf.fields.aggregate(Max("order"))["order__max"] or 0) + 1
            field.save()
            messages.success(request, "Champ ajouté.")
        else:
            messages.error(request, "Erreur dans le formulaire.")
        return redirect("logistics:settings", event_slug=event_slug)


class FieldEditView(OrganizerRequiredMixin, View):
    def _get_lf_and_field(self, field_id):
        lf = _get_or_create_logistics_form(self.event)
        field = get_object_or_404(LogisticsField, pk=field_id, form=lf)
        return lf, field

    def get(self, request, event_slug, field_id):
        lf, field = self._get_lf_and_field(field_id)
        form = LogisticsFieldForm(instance=field)
        return render(
            request,
            "logistics/field_edit.html",
            {"event": self.event, "logistics_form": lf, "field": field, "form": form},
        )

    def post(self, request, event_slug, field_id):
        lf, field = self._get_lf_and_field(field_id)
        form = LogisticsFieldForm(request.POST, instance=field)
        if form.is_valid():
            form.save()
            messages.success(request, "Champ modifié.")
            return redirect("logistics:settings", event_slug=event_slug)
        return render(
            request,
            "logistics/field_edit.html",
            {"event": self.event, "logistics_form": lf, "field": field, "form": form},
        )


class FieldDeleteView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, field_id):
        lf = _get_or_create_logistics_form(self.event)
        field = get_object_or_404(LogisticsField, pk=field_id, form=lf)
        field.delete()
        messages.success(request, "Champ supprimé.")
        return redirect("logistics:settings", event_slug=event_slug)


class FieldReorderView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug):
        lf = _get_or_create_logistics_form(self.event)
        try:
            payload = json.loads(request.body)
        except (ValueError, TypeError):
            return JsonResponse({"error": "JSON invalide"}, status=400)
        if not isinstance(payload, list):
            return JsonResponse({"error": "Liste attendue"}, status=400)
        updates = []
        for item in payload:
            pk = item.get("id")
            order = item.get("order")
            if not isinstance(order, int) or order <= 0:
                return JsonResponse({"error": "Ordre invalide"}, status=400)
            updates.append(LogisticsField(pk=pk, order=order))
        ids = [f.pk for f in updates]
        owned = set(lf.fields.filter(pk__in=ids).values_list("pk", flat=True))
        if owned != set(ids):
            return JsonResponse({"error": "Champ non trouvé"}, status=404)
        LogisticsField.objects.bulk_update(updates, ["order"])
        return JsonResponse({"ok": True})


# ---------------------------------------------------------------------------
# Organizer: manage responses
# ---------------------------------------------------------------------------


class ResponseListView(CommitteeRequiredMixin, View):
    def get(self, request, event_slug):
        lf = _get_or_create_logistics_form(self.event)
        responses = (
            lf.responses.select_related("proposal")
            .prefetch_related("field_responses__field")
            .order_by("respondent_name")
        )
        fields = lf.fields.order_by("order")
        return render(
            request,
            "logistics/response_list.html",
            {
                "event": self.event,
                "logistics_form": lf,
                "responses": responses,
                "fields": fields,
            },
        )


class ResponseDetailView(CommitteeRequiredMixin, View):
    def get(self, request, event_slug, response_id):
        lf = _get_or_create_logistics_form(self.event)
        response = get_object_or_404(
            LogisticsResponse.objects.prefetch_related("field_responses__field"),
            pk=response_id,
            form=lf,
        )
        return render(
            request,
            "logistics/response_detail.html",
            {"event": self.event, "logistics_form": lf, "response": response},
        )


class ResponseCreateView(OrganizerRequiredMixin, View):
    """Création manuelle d'une entrée de réponse par l'organisateur."""

    def get(self, request, event_slug):
        lf = _get_or_create_logistics_form(self.event)
        form = LogisticsResponseAdminForm()
        form.fields["proposal"].queryset = self.event.proposals.filter(
            status="accepted"
        ).order_by("title")
        return render(
            request,
            "logistics/response_create.html",
            {"event": self.event, "logistics_form": lf, "form": form},
        )

    def post(self, request, event_slug):
        lf = _get_or_create_logistics_form(self.event)
        form = LogisticsResponseAdminForm(request.POST)
        form.fields["proposal"].queryset = self.event.proposals.filter(
            status="accepted"
        ).order_by("title")
        if form.is_valid():
            resp = form.save(commit=False)
            resp.form = lf
            resp.save()
            messages.success(request, "Entrée créée.")
            return redirect("logistics:response_list", event_slug=event_slug)
        return render(
            request,
            "logistics/response_create.html",
            {"event": self.event, "logistics_form": lf, "form": form},
        )


class ResponseDeleteView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, response_id):
        lf = _get_or_create_logistics_form(self.event)
        response = get_object_or_404(LogisticsResponse, pk=response_id, form=lf)
        response.hard_delete()
        messages.success(request, "Réponse supprimée.")
        return redirect("logistics:response_list", event_slug=event_slug)


class SendLinkView(OrganizerRequiredMixin, View):
    """(Re)envoie le lien d'accès à un intervenant."""

    def post(self, request, event_slug, response_id):
        lf = _get_or_create_logistics_form(self.event)
        response = get_object_or_404(LogisticsResponse, pk=response_id, form=lf)
        send_logistics_link(response, request=request)
        messages.success(request, f"Lien envoyé à {response.respondent_email}.")
        return redirect("logistics:response_list", event_slug=event_slug)


class SendAllLinksView(OrganizerRequiredMixin, View):
    """Envoie le lien à toutes les entrées qui n'ont pas encore répondu."""

    def post(self, request, event_slug):
        lf = _get_or_create_logistics_form(self.event)
        pending = lf.responses.filter(is_complete=False)
        count = 0
        for response in pending:
            send_logistics_link(response, request=request)
            count += 1
        messages.success(request, f"{count} lien(s) envoyé(s).")
        return redirect("logistics:response_list", event_slug=event_slug)


# ---------------------------------------------------------------------------
# Public: respond via token
# ---------------------------------------------------------------------------


class PublicRespondView(View):
    def _get_response(self, token):
        return get_object_or_404(
            LogisticsResponse.objects.select_related("form__event"), token=token
        )

    def _is_open(self, lf):
        if not lf.is_open:
            return False
        if lf.deadline and timezone.now() > lf.deadline:
            return False
        return True

    def get(self, request, token):
        response = self._get_response(token)
        lf = response.form
        editable = self._is_open(lf)
        form, fields = build_response_form(lf, instance=response)
        return render(
            request,
            "logistics/public_respond.html",
            {
                "logistics_form": lf,
                "event": lf.event,
                "response": response,
                "form": form,
                "fields": fields,
                "editable": editable,
            },
        )

    def post(self, request, token):
        response = self._get_response(token)
        lf = response.form
        if not self._is_open(lf):
            raise PermissionDenied
        form, fields = build_response_form(lf, data=request.POST, instance=response)
        if form.is_valid():
            _save_response(form, response, fields)
            return redirect("logistics:respond_done", token=token)
        return render(
            request,
            "logistics/public_respond.html",
            {
                "logistics_form": lf,
                "event": lf.event,
                "response": response,
                "form": form,
                "fields": fields,
                "editable": True,
            },
        )


def _save_response(form, response, fields):
    for field in fields:
        key = f"field_{field.pk}"
        raw = form.cleaned_data.get(key, "")
        if field.kind == LogisticsField.Kind.MULTICHOICE and isinstance(raw, list):
            value = json.dumps(raw)
        elif isinstance(raw, bool):
            value = "true" if raw else ""
        else:
            value = str(raw) if raw is not None else ""
        LogisticsFieldResponse.objects.update_or_create(
            response=response,
            field=field,
            defaults={"value": value},
        )
    response.is_complete = True
    response.save(update_fields=["is_complete", "updated_at"])


class PublicRespondDoneView(View):
    def get(self, request, token):
        response = get_object_or_404(LogisticsResponse, token=token)
        return render(
            request,
            "logistics/public_respond_done.html",
            {"event": response.form.event, "response": response},
        )
