import csv
import json

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Max, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.core.mixins import CommitteeRequiredMixin, OrganizerRequiredMixin

from .forms import (
    BudgetChargeForm,
    BudgetDocumentForm,
    BudgetLineForm,
    BudgetSettingsForm,
    LogisticsFieldForm,
    LogisticsFormSettingsForm,
    LogisticsResponseAdminForm,
    build_response_form,
)
from .mail import send_logistics_link
from .models import (
    BudgetCharge,
    BudgetDocument,
    BudgetLine,
    BudgetSettings,
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
    def _stats(self):
        from decimal import Decimal
        zero = Decimal("0.00")
        pending_responses = LogisticsResponse.objects.filter(
            form__event=self.event, is_complete=False
        ).count()
        pending_charges = BudgetCharge.objects.filter(
            budget_line__event=self.event, status=BudgetCharge.Status.PENDING
        ).count()
        budget_planned = (
            self.event.budget_lines.aggregate(s=Sum("amount_planned"))["s"] or zero
        )
        budget_actual = (
            self.event.budget_lines
            .filter(amount_actual__isnull=False)
            .aggregate(s=Sum("amount_actual"))["s"] or zero
        )
        return {
            "stat_pending_responses": pending_responses,
            "stat_pending_charges": pending_charges,
            "stat_budget_planned": budget_planned,
            "stat_budget_actual": budget_actual,
        }

    def get(self, request, event_slug):
        logistics_forms = (
            self.event.logistics_forms
            .annotate(response_count=Count("responses"))
            .order_by("created_at")
        )
        ctx = {
            "event": self.event,
            "membership": self.membership,
            "logistics_forms": logistics_forms,
            "create_form": LogisticsFormSettingsForm(),
        }
        ctx.update(self._stats())
        return render(request, "logistics/index.html", ctx)

    def post(self, request, event_slug):
        form = LogisticsFormSettingsForm(request.POST)
        if form.is_valid():
            lf = form.save(commit=False)
            lf.event = self.event
            lf.save()
            messages.success(request, "Formulaire créé.")
            return redirect("logistics:settings", event_slug=event_slug, form_id=lf.pk)
        ctx = {
            "event": self.event,
            "membership": self.membership,
            "logistics_forms": (
                self.event.logistics_forms
                .annotate(response_count=Count("responses"))
                .order_by("created_at")
            ),
            "create_form": form,
        }
        ctx.update(self._stats())
        return render(request, "logistics/index.html", ctx)


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
# Prises en charge (intégrées dans le budget)
# ---------------------------------------------------------------------------


class BudgetChargeCreateView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, line_pk):
        line = get_object_or_404(BudgetLine, pk=line_pk, event=self.event)
        form = BudgetChargeForm(request.POST, event=self.event)
        if form.is_valid():
            charge = form.save(commit=False)
            charge.budget_line = line
            charge.save()
            messages.success(request, "Prise en charge ajoutée.")
        else:
            messages.error(request, "Erreur dans le formulaire.")
        return redirect("logistics:budget", event_slug=event_slug)



class BudgetChargeDeleteView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, charge_pk):
        charge = get_object_or_404(BudgetCharge, pk=charge_pk, budget_line__event=self.event)
        charge.hard_delete()
        messages.success(request, "Prise en charge supprimée.")
        return redirect("logistics:budget", event_slug=event_slug)


class BudgetChargeStatusView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, charge_pk):
        charge = get_object_or_404(BudgetCharge, pk=charge_pk, budget_line__event=self.event)
        try:
            data = json.loads(request.body)
            status = data["status"]
        except (ValueError, KeyError):
            return JsonResponse({"error": "Données invalides."}, status=400)
        if status not in BudgetCharge.Status.values:
            return JsonResponse({"error": "Statut invalide."}, status=400)
        charge.status = status
        charge.save(update_fields=["status", "updated_at"])
        return JsonResponse({"status": charge.status, "label": charge.get_status_display()})


class BudgetChargeExportView(OrganizerRequiredMixin, View):
    def get(self, request, event_slug):
        charges = (
            BudgetCharge.objects.filter(budget_line__event=self.event)
            .select_related("budget_line")
            .order_by("budget_line__category", "person_name")
        )
        http_response = HttpResponse(content_type="text/csv; charset=utf-8")
        http_response["Content-Disposition"] = (
            f'attachment; filename="prises-en-charge-{self.event.slug}.csv"'
        )
        http_response.write("﻿")
        writer = csv.writer(http_response)
        writer.writerow(["Poste", "Catégorie", "Nom", "Email", "Description", "Montant (€)", "Statut", "Notes"])
        for c in charges:
            writer.writerow([
                c.budget_line.label,
                c.budget_line.get_category_display(),
                c.person_name, c.person_email, c.description,
                c.amount, c.get_status_display(), c.notes,
            ])
        return http_response


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------


class BudgetView(OrganizerRequiredMixin, View):
    def _ctx(self, form=None):
        from decimal import Decimal

        from django.db.models import Sum
        zero = Decimal("0.00")

        lines = list(
            self.event.budget_lines
            .prefetch_related("documents", "charges")
            .order_by("category", "label")
        )

        categories = []
        for val, label in BudgetLine.Category.choices:
            cat_lines = [ln for ln in lines if ln.category == val]
            if cat_lines:
                total_planned = sum(ln.amount_planned for ln in cat_lines)
                total_actual = sum(
                    ln.amount_actual for ln in cat_lines if ln.amount_actual is not None
                ) or zero
                categories.append({
                    "value": val,
                    "label": label,
                    "lines": cat_lines,
                    "total_planned": total_planned,
                    "total_actual": total_actual,
                })

        total_planned = sum(ln.amount_planned for ln in lines) or zero
        total_actual = sum(
            ln.amount_actual for ln in lines if ln.amount_actual is not None
        ) or zero
        total_charges_received = (
            BudgetCharge.objects.filter(
                budget_line__event=self.event,
                status=BudgetCharge.Status.RECEIVED,
            ).aggregate(s=Sum("amount"))["s"] or zero
        )

        settings_obj, _ = BudgetSettings.objects.get_or_create(event=self.event)
        envelope = settings_obj.envelope
        remaining = (envelope - total_planned) if envelope is not None else None

        return {
            "event": self.event,
            "membership": self.membership,
            "lines": lines,
            "categories": categories,
            "total_planned": total_planned,
            "total_actual": total_actual,
            "total_charges_received": total_charges_received,
            "envelope": envelope,
            "remaining": remaining,
            "form": form or BudgetLineForm(),
            "doc_form": BudgetDocumentForm(),
            "category_choices": BudgetLine.Category.choices,
            "charge_status_choices": BudgetCharge.Status.choices,
        }

    def get(self, request, event_slug):
        return render(request, "logistics/budget.html", self._ctx())

    def post(self, request, event_slug):
        form = BudgetLineForm(request.POST)
        if form.is_valid():
            line = form.save(commit=False)
            line.event = self.event
            line.save()
            messages.success(request, "Poste ajouté.")
            return redirect("logistics:budget", event_slug=event_slug)
        return render(request, "logistics/budget.html", self._ctx(form=form))


class BudgetEnvelopeView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug):
        settings_obj, _ = BudgetSettings.objects.get_or_create(event=self.event)
        form = BudgetSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Enveloppe mise à jour.")
        else:
            messages.error(request, "Montant invalide.")
        return redirect("logistics:budget", event_slug=event_slug)


class BudgetLineEditView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, pk):
        line = get_object_or_404(BudgetLine, pk=pk, event=self.event)
        form = BudgetLineForm(request.POST, instance=line)
        if form.is_valid():
            form.save()
            messages.success(request, "Poste mis à jour.")
        else:
            messages.error(request, "Erreur dans le formulaire.")
        return redirect("logistics:budget", event_slug=event_slug)


class BudgetLineDeleteView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, pk):
        line = get_object_or_404(BudgetLine, pk=pk, event=self.event)
        line.hard_delete()
        messages.success(request, "Poste supprimé.")
        return redirect("logistics:budget", event_slug=event_slug)


class BudgetDocumentUploadView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, line_pk):
        line = get_object_or_404(BudgetLine, pk=line_pk, event=self.event)
        form = BudgetDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.line = line
            doc.save()
            messages.success(request, "Document ajouté.")
        else:
            messages.error(request, "Erreur dans le formulaire.")
        return redirect("logistics:budget", event_slug=event_slug)


class BudgetDocumentDeleteView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, doc_pk):
        doc = get_object_or_404(BudgetDocument, pk=doc_pk, line__event=self.event)
        doc.delete()
        messages.success(request, "Document supprimé.")
        return redirect("logistics:budget", event_slug=event_slug)


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
