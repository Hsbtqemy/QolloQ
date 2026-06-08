import csv
import json

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Max
from django.http import HttpResponse, JsonResponse
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


def _get_lf(event, form_id):
    return get_object_or_404(LogisticsForm, pk=form_id, event=event)


# ---------------------------------------------------------------------------
# Organizer: liste des formulaires de l'événement
# ---------------------------------------------------------------------------


class LogisticsIndexView(OrganizerRequiredMixin, View):
    def get(self, request, event_slug):
        forms = self.event.logistics_forms.annotate_response_count().order_by("created_at") \
            if hasattr(LogisticsForm, 'annotate_response_count') \
            else self.event.logistics_forms.order_by("created_at")
        return render(request, "logistics/index.html", {
            "event": self.event,
            "membership": self.membership,
            "logistics_forms": self.event.logistics_forms.order_by("created_at"),
            "create_form": LogisticsFormSettingsForm(),
        })

    def post(self, request, event_slug):
        form = LogisticsFormSettingsForm(request.POST)
        if form.is_valid():
            lf = form.save(commit=False)
            lf.event = self.event
            lf.save()
            messages.success(request, "Formulaire créé.")
            return redirect("logistics:settings", event_slug=event_slug, form_id=lf.pk)
        return render(request, "logistics/index.html", {
            "event": self.event,
            "membership": self.membership,
            "logistics_forms": self.event.logistics_forms.order_by("created_at"),
            "create_form": form,
        })


# ---------------------------------------------------------------------------
# Organizer: configure a specific form
# ---------------------------------------------------------------------------


class LogisticsSettingsView(OrganizerRequiredMixin, View):
    def get(self, request, event_slug, form_id):
        lf = _get_lf(self.event, form_id)
        form = LogisticsFormSettingsForm(instance=lf)
        fields = lf.fields.order_by("order")
        return render(request, "logistics/settings.html", {
            "event": self.event,
            "membership": self.membership,
            "logistics_form": lf,
            "form": form,
            "fields": fields,
        })

    def post(self, request, event_slug, form_id):
        lf = _get_lf(self.event, form_id)
        form = LogisticsFormSettingsForm(request.POST, instance=lf)
        if form.is_valid():
            form.save()
            messages.success(request, "Paramètres enregistrés.")
            return redirect("logistics:settings", event_slug=event_slug, form_id=form_id)
        fields = lf.fields.order_by("order")
        return render(request, "logistics/settings.html", {
            "event": self.event,
            "membership": self.membership,
            "logistics_form": lf,
            "form": form,
            "fields": fields,
        })


class LogisticsFormDeleteView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, form_id):
        lf = _get_lf(self.event, form_id)
        lf.delete()
        messages.success(request, "Formulaire supprimé.")
        return redirect("logistics:index", event_slug=event_slug)


class FieldCreateView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, form_id):
        lf = _get_lf(self.event, form_id)
        form = LogisticsFieldForm(request.POST)
        if form.is_valid():
            field = form.save(commit=False)
            field.form = lf
            field.order = (lf.fields.aggregate(Max("order"))["order__max"] or 0) + 1
            field.save()
            messages.success(request, "Champ ajouté.")
        else:
            messages.error(request, "Erreur dans le formulaire.")
        return redirect("logistics:settings", event_slug=event_slug, form_id=form_id)


class FieldEditView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, form_id, field_id):
        lf = _get_lf(self.event, form_id)
        field = get_object_or_404(LogisticsField, pk=field_id, form=lf)
        form = LogisticsFieldForm(request.POST, instance=field)
        if form.is_valid():
            form.save()
            messages.success(request, "Champ modifié.")
        else:
            messages.error(request, "Erreur dans le formulaire.")
        return redirect("logistics:settings", event_slug=event_slug, form_id=form_id)


class FieldDeleteView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, form_id, field_id):
        lf = _get_lf(self.event, form_id)
        field = get_object_or_404(LogisticsField, pk=field_id, form=lf)
        field.delete()
        messages.success(request, "Champ supprimé.")
        return redirect("logistics:settings", event_slug=event_slug, form_id=form_id)


class FieldReorderView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, form_id):
        lf = _get_lf(self.event, form_id)
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
# Organizer / committee: manage responses
# ---------------------------------------------------------------------------


class ResponseListView(CommitteeRequiredMixin, View):
    def get(self, request, event_slug, form_id):
        lf = _get_lf(self.event, form_id)
        responses = (
            lf.responses
            .prefetch_related("field_responses__field")
            .order_by("respondent_name")
        )
        fields = lf.fields.order_by("order")
        return render(request, "logistics/response_list.html", {
            "event": self.event,
            "membership": self.membership,
            "logistics_form": lf,
            "responses": responses,
            "fields": fields,
        })


class ResponseDetailView(CommitteeRequiredMixin, View):
    def get(self, request, event_slug, form_id, response_id):
        lf = _get_lf(self.event, form_id)
        response = get_object_or_404(
            LogisticsResponse.objects.prefetch_related("field_responses__field"),
            pk=response_id,
            form=lf,
        )
        return render(request, "logistics/response_detail.html", {
            "event": self.event,
            "membership": self.membership,
            "logistics_form": lf,
            "response": response,
        })


class ResponseCreateView(OrganizerRequiredMixin, View):
    def get(self, request, event_slug, form_id):
        lf = _get_lf(self.event, form_id)
        return render(request, "logistics/response_create.html", {
            "event": self.event,
            "membership": self.membership,
            "logistics_form": lf,
            "form": LogisticsResponseAdminForm(),
        })

    def post(self, request, event_slug, form_id):
        lf = _get_lf(self.event, form_id)
        form = LogisticsResponseAdminForm(request.POST)
        if form.is_valid():
            resp = form.save(commit=False)
            resp.form = lf
            resp.save()
            messages.success(request, "Entrée créée.")
            return redirect("logistics:response_list", event_slug=event_slug, form_id=form_id)
        return render(request, "logistics/response_create.html", {
            "event": self.event,
            "membership": self.membership,
            "logistics_form": lf,
            "form": form,
        })


class ResponseDeleteView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, form_id, response_id):
        lf = _get_lf(self.event, form_id)
        response = get_object_or_404(LogisticsResponse, pk=response_id, form=lf)
        response.hard_delete()
        messages.success(request, "Réponse supprimée.")
        return redirect("logistics:response_list", event_slug=event_slug, form_id=form_id)


class SendLinkView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, form_id, response_id):
        lf = _get_lf(self.event, form_id)
        response = get_object_or_404(LogisticsResponse, pk=response_id, form=lf)
        send_logistics_link(response, request=request)
        messages.success(request, f"Lien envoyé à {response.respondent_email}.")
        return redirect("logistics:response_list", event_slug=event_slug, form_id=form_id)


class SendAllLinksView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, form_id):
        lf = _get_lf(self.event, form_id)
        pending = lf.responses.filter(is_complete=False)
        count = 0
        for response in pending:
            send_logistics_link(response, request=request)
            count += 1
        messages.success(request, f"{count} lien(s) envoyé(s).")
        return redirect("logistics:response_list", event_slug=event_slug, form_id=form_id)


class ResponseExportView(OrganizerRequiredMixin, View):
    def get(self, request, event_slug, form_id):
        lf = _get_lf(self.event, form_id)
        fields = list(lf.fields.order_by("order"))
        responses = (
            lf.responses
            .prefetch_related("field_responses__field")
            .order_by("respondent_name")
        )
        http_response = HttpResponse(content_type="text/csv; charset=utf-8")
        http_response["Content-Disposition"] = (
            f'attachment; filename="logistique-{self.event.slug}.csv"'
        )
        http_response.write("﻿")  # BOM pour Excel
        writer = csv.writer(http_response)
        writer.writerow(
            ["Nom", "Email", "Complète"] + [f.label for f in fields]
        )
        for resp in responses:
            field_values = {fr.field_id: fr.display_value for fr in resp.field_responses.all()}
            writer.writerow(
                [resp.respondent_name, resp.respondent_email, "Oui" if resp.is_complete else "Non"]
                + [field_values.get(f.pk, "") for f in fields]
            )
        return http_response


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
        return render(request, "logistics/public_respond.html", {
            "logistics_form": lf,
            "event": lf.event,
            "response": response,
            "form": form,
            "fields": fields,
            "editable": editable,
        })

    def post(self, request, token):
        response = self._get_response(token)
        lf = response.form
        if not self._is_open(lf):
            raise PermissionDenied
        form, fields = build_response_form(lf, data=request.POST, instance=response)
        if form.is_valid():
            _save_response(form, response, fields)
            return redirect("logistics:respond_done", token=token)
        return render(request, "logistics/public_respond.html", {
            "logistics_form": lf,
            "event": lf.event,
            "response": response,
            "form": form,
            "fields": fields,
            "editable": True,
        })


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
        return render(request, "logistics/public_respond_done.html", {
            "event": response.form.event,
            "response": response,
        })
