import json

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from apps.core.mixins import CommitteeRequiredMixin, OrganizerRequiredMixin, PublicLangMixin
from apps.events.models import Event, Membership

from .forms import (
    AuthorFormSet,
    EvaluationForm,
    OrganizerProposalForm,
    PublicProposalForm,
    ResendTokenForm,
    SubmissionFieldForm,
    SubmissionInstructionsForm,
)
from .mail import send_submission_confirmation, send_token_reminder
from .models import Evaluation, Proposal, SubmissionField


# ── Vues publiques (sans compte) ─────────────────────────────────────────────

class PublicSubmitView(PublicLangMixin, View):
    """Formulaire public de soumission diffusé par l'organisateur."""

    def _get_open_event(self, event_slug):
        event = get_object_or_404(Event, slug=event_slug)
        if not event.submissions_open:
            raise Http404
        if event.submission_deadline and event.submission_deadline < timezone.now():
            raise Http404
        return event

    def get(self, request, event_slug):
        event = self._get_open_event(event_slug)
        return render(request, "submissions/public_submit.html", {
            "event": event,
            "form": PublicProposalForm(event=event, lang=self.lang),
            "author_formset": AuthorFormSet(),
            "lang": self.lang,
        })

    def post(self, request, event_slug):
        event = self._get_open_event(event_slug)
        form = PublicProposalForm(request.POST, event=event, lang=self.lang)
        author_formset = AuthorFormSet(request.POST)
        if form.is_valid() and author_formset.is_valid():
            proposal = form.save(commit=False)
            proposal.event = event
            proposal.save()
            author_formset.instance = proposal
            author_formset.save()
            form.save_custom_responses(proposal)
            send_submission_confirmation(proposal)
            return redirect("submissions:submitted", token=str(proposal.token))
        return render(request, "submissions/public_submit.html", {
            "event": event,
            "form": form,
            "author_formset": author_formset,
            "lang": self.lang,
        })


class SubmissionSubmittedView(PublicLangMixin, View):
    """Page de confirmation après soumission."""

    def get(self, request, token):
        proposal = get_object_or_404(Proposal, token=token)
        return render(request, "submissions/submitted.html", {
            "proposal": proposal,
            "event": proposal.event,
            "lang": self.lang,
        })


class TokenAccessView(PublicLangMixin, View):
    """Accès soumissionnaire via lien tokenisé : consulter, modifier, retirer."""

    def _is_still_editable(self, proposal):
        if not proposal.is_editable:
            return False
        deadline = proposal.event.submission_deadline
        if deadline and deadline < timezone.now():
            return False
        return True

    def get(self, request, token):
        proposal = get_object_or_404(Proposal.objects.select_related("event").prefetch_related("field_responses__field"), token=token)
        editable = self._is_still_editable(proposal)
        event = proposal.event
        return render(request, "submissions/token_access.html", {
            "proposal": proposal,
            "event": event,
            "editable": editable,
            "form": PublicProposalForm(instance=proposal, event=event, lang=self.lang) if editable else None,
            "author_formset": AuthorFormSet(instance=proposal) if editable else None,
            "lang": self.lang,
        })

    def post(self, request, token):
        proposal = get_object_or_404(Proposal.objects.select_related("event").prefetch_related("field_responses__field"), token=token)
        if not self._is_still_editable(proposal):
            raise PermissionDenied

        action = request.POST.get("action")
        if action == "withdraw":
            event = proposal.event
            proposal.hard_delete()
            return render(request, "submissions/withdrawn.html", {"event": event, "lang": self.lang})

        event = proposal.event
        form = PublicProposalForm(request.POST, instance=proposal, event=event, lang=self.lang)
        author_formset = AuthorFormSet(request.POST, instance=proposal)
        if form.is_valid() and author_formset.is_valid():
            proposal = form.save()
            author_formset.save()
            form.save_custom_responses(proposal)
            messages.success(request, "Votre proposition a été mise à jour.")
            return redirect("submissions:token_access", token=token)
        return render(request, "submissions/token_access.html", {
            "proposal": proposal,
            "event": event,
            "editable": True,
            "form": form,
            "author_formset": author_formset,
            "lang": self.lang,
        })


class ResendTokenView(PublicLangMixin, View):
    """Renvoi du lien tokenisé sur saisie de l'email."""

    def get(self, request, event_slug):
        event = get_object_or_404(Event, slug=event_slug)
        return render(request, "submissions/resend_token.html", {
            "event": event,
            "form": ResendTokenForm(),
            "lang": self.lang,
        })

    def post(self, request, event_slug):
        event = get_object_or_404(Event, slug=event_slug)
        form = ResendTokenForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            for proposal in Proposal.objects.filter(event=event, submitter_email=email):
                send_token_reminder(proposal)
            return render(request, "submissions/resend_token_sent.html", {"event": event, "lang": self.lang})
        return render(request, "submissions/resend_token.html", {"event": event, "form": form, "lang": self.lang})


# ── Vues organisateur / comité ────────────────────────────────────────────────

class ProposalListView(CommitteeRequiredMixin, View):
    def get(self, request, event_slug):
        proposals = (
            Proposal.objects.filter(event=self.event)
            .prefetch_related("authors", "evaluations")
            .order_by("-created_at")
        )
        submit_url = request.build_absolute_uri(
            reverse("submissions:public_submit", kwargs={"event_slug": event_slug})
        )
        return render(request, "submissions/organizer/list.html", {
            "event": self.event,
            "membership": self.membership,
            "proposals": proposals,
            "status_choices": Proposal.Status.choices,
            "submit_url": submit_url,
        })


class ProposalDetailView(CommitteeRequiredMixin, View):
    def get(self, request, event_slug, proposal_id):
        proposal = get_object_or_404(
            Proposal.objects.prefetch_related("authors", "field_responses__field"),
            pk=proposal_id,
            event=self.event,
        )
        evaluations = self._get_visible_evaluations(proposal)
        own_evaluation = Evaluation.objects.filter(
            proposal=proposal, evaluator=self.membership
        ).first()
        return render(request, "submissions/organizer/detail.html", {
            "event": self.event,
            "membership": self.membership,
            "proposal": proposal,
            "evaluations": evaluations,
            "own_evaluation": own_evaluation,
            "eval_form": EvaluationForm(instance=own_evaluation),
            "organizer_form": OrganizerProposalForm(instance=proposal, event=self.event) if self.membership.is_organizer else None,
            "status_choices": Proposal.Status.choices,
        })

    def _get_visible_evaluations(self, proposal):
        # Les organisateurs voient toujours tout
        if self.membership.is_organizer:
            return proposal.evaluations.select_related("evaluator").all()

        # Pour le comité : respect du paramètre eval_visibility
        own_exists = Evaluation.objects.filter(
            proposal=proposal, evaluator=self.membership
        ).exists()
        if self.event.eval_visibility == Event.EvalVisibility.AFTER_OWN and not own_exists:
            return Evaluation.objects.none()

        # Anonymat inter-évaluateurs
        if self.event.eval_anonymous:
            return proposal.evaluations.all()  # template masque les noms
        return proposal.evaluations.select_related("evaluator").all()


class ProposalStatusView(OrganizerRequiredMixin, View):
    """Changement de statut d'une proposition (POST JSON)."""

    def post(self, request, event_slug, proposal_id):
        proposal = get_object_or_404(Proposal, pk=proposal_id, event=self.event)
        try:
            data = json.loads(request.body)
            status = data["status"]
        except (ValueError, KeyError):
            return JsonResponse({"error": "Données invalides."}, status=400)
        if status not in Proposal.Status.values:
            return JsonResponse({"error": "Statut invalide."}, status=400)
        proposal.status = status
        proposal.save(update_fields=["status", "updated_at"])
        return JsonResponse({"status": proposal.status, "label": proposal.get_status_display()})


class ProposalEditView(OrganizerRequiredMixin, View):
    """Modification d'une proposition par l'organisateur."""

    def post(self, request, event_slug, proposal_id):
        proposal = get_object_or_404(
            Proposal.objects.prefetch_related("field_responses__field"),
            pk=proposal_id,
            event=self.event,
        )
        form = OrganizerProposalForm(request.POST, instance=proposal, event=self.event)
        author_formset = AuthorFormSet(request.POST, instance=proposal)
        if form.is_valid() and author_formset.is_valid():
            form.save()
            author_formset.save()
            form.save_custom_responses(proposal)
            messages.success(request, "Proposition mise à jour.")
        return redirect("submissions:detail", event_slug=event_slug, proposal_id=proposal_id)


class EvaluationSubmitView(CommitteeRequiredMixin, View):
    """Dépôt ou mise à jour d'un avis par un membre du comité."""

    def post(self, request, event_slug, proposal_id):
        proposal = get_object_or_404(Proposal, pk=proposal_id, event=self.event)
        existing = Evaluation.objects.filter(
            proposal=proposal, evaluator=self.membership
        ).first()
        form = EvaluationForm(request.POST, instance=existing)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.proposal = proposal
            evaluation.evaluator = self.membership
            evaluation.save()
            messages.success(request, "Avis enregistré.")
        return redirect("submissions:detail", event_slug=event_slug, proposal_id=proposal_id)


class ProposalCreateView(OrganizerRequiredMixin, View):
    """Saisie directe d'une proposition par l'organisateur (hors flux public)."""

    def get(self, request, event_slug):
        return render(request, "submissions/organizer/create.html", {
            "event": self.event,
            "membership": self.membership,
            "form": OrganizerProposalForm(event=self.event),
            "author_formset": AuthorFormSet(),
        })

    def post(self, request, event_slug):
        form = OrganizerProposalForm(request.POST, event=self.event)
        author_formset = AuthorFormSet(request.POST)
        if form.is_valid() and author_formset.is_valid():
            proposal = form.save(commit=False)
            proposal.event = self.event
            proposal.save()
            author_formset.instance = proposal
            author_formset.save()
            form.save_custom_responses(proposal)
            messages.success(request, "Proposition créée.")
            return redirect("submissions:detail", event_slug=event_slug, proposal_id=proposal.pk)
        return render(request, "submissions/organizer/create.html", {
            "event": self.event,
            "membership": self.membership,
            "form": form,
            "author_formset": author_formset,
        })


# ── Paramétrage du formulaire de dépôt ───────────────────────────────────────

class SubmissionFormSettingsView(OrganizerRequiredMixin, View):
    def _ctx(self, instructions_form=None):
        return {
            "event": self.event,
            "membership": self.membership,
            "fields": self.event.submission_fields.order_by("order"),
            "instructions_form": instructions_form or SubmissionInstructionsForm(instance=self.event),
            "field_form": SubmissionFieldForm(),
        }

    def get(self, request, event_slug):
        return render(request, "submissions/organizer/form_settings.html", self._ctx())

    def post(self, request, event_slug):
        form = SubmissionInstructionsForm(request.POST, instance=self.event)
        if form.is_valid():
            form.save()
            messages.success(request, "Instructions enregistrées.")
            return redirect("submissions:form_settings", event_slug=event_slug)
        return render(request, "submissions/organizer/form_settings.html",
                      self._ctx(instructions_form=form))


class SubmissionFieldToggleView(OrganizerRequiredMixin, View):
    _ALLOWED = frozenset({
        "submission_show_keywords",
        "submission_show_format",
        "submission_show_availability",
    })

    def post(self, request, event_slug):
        try:
            data = json.loads(request.body)
            field = data["field"]
            value = bool(data["value"])
        except (ValueError, KeyError, TypeError):
            return JsonResponse({"error": "Données invalides."}, status=400)
        if field not in self._ALLOWED:
            return JsonResponse({"error": "Champ non autorisé."}, status=400)
        setattr(self.event, field, value)
        self.event.save(update_fields=[field, "updated_at"])
        return JsonResponse({"ok": True})


class SubmissionFieldCreateView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug):
        form = SubmissionFieldForm(request.POST)
        if form.is_valid():
            field = form.save(commit=False)
            field.event = self.event
            last = (
                SubmissionField.objects.filter(event=self.event)
                .order_by("-order")
                .values_list("order", flat=True)
                .first()
            )
            field.order = (last or 0) + 1
            field.save()
            messages.success(request, "Champ ajouté.")
        else:
            messages.error(request, "Erreur dans le formulaire.")
        return redirect("submissions:form_settings", event_slug=event_slug)


class SubmissionFieldDeleteView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, field_id):
        field = get_object_or_404(SubmissionField, pk=field_id, event=self.event)
        field.delete()
        messages.success(request, "Champ supprimé.")
        return redirect("submissions:form_settings", event_slug=event_slug)


class SubmissionFieldReorderView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug):
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
            updates.append(SubmissionField(pk=pk, order=order))
        ids = [f.pk for f in updates]
        owned = set(
            SubmissionField.objects.filter(event=self.event, pk__in=ids)
            .values_list("pk", flat=True)
        )
        if owned != set(ids):
            return JsonResponse({"error": "Champ non trouvé"}, status=404)
        SubmissionField.objects.bulk_update(updates, ["order"])
        return JsonResponse({"ok": True})


class AttendanceUpdateView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, proposal_id):
        proposal = get_object_or_404(Proposal, event=self.event, pk=proposal_id)
        attendance = request.POST.get("attendance", "")
        if attendance in Proposal.Attendance.values:
            proposal.attendance = attendance
            proposal.save(update_fields=["attendance", "updated_at"])
        return JsonResponse({"attendance": proposal.attendance})


# ── Évaluation tokenisée (sans compte) ──────────────────────────────────────

class EvaluatorAccessView(View):
    """Accès comité via lien tokenisé : liste des propositions + formulaires d'évaluation."""

    def _get_membership(self, token):
        return get_object_or_404(Membership, eval_token=token)

    def _get_proposals(self, membership):
        event = membership.event
        if event.eval_assignment == Event.EvalAssignment.MANUAL:
            return (
                membership.assigned_proposals
                .filter(event=event)
                .prefetch_related("authors")
                .order_by("title")
            )
        return (
            Proposal.objects.filter(event=event)
            .prefetch_related("authors")
            .order_by("title")
        )

    def get(self, request, token):
        membership = self._get_membership(token)
        proposals = self._get_proposals(membership)
        own_evals = {
            e.proposal_id: e
            for e in Evaluation.objects.filter(evaluator=membership)
        }
        return render(request, "submissions/evaluator/access.html", {
            "event": membership.event,
            "membership": membership,
            "proposals": proposals,
            "own_evals": own_evals,
            "verdict_choices": Evaluation.Verdict.choices,
            "token": str(token),
        })


class EvaluatorEvalView(View):
    """Dépôt ou mise à jour d'un avis via lien tokenisé."""

    def post(self, request, token, proposal_id):
        membership = get_object_or_404(Membership, eval_token=token)
        proposal = get_object_or_404(Proposal, pk=proposal_id, event=membership.event)
        existing = Evaluation.objects.filter(proposal=proposal, evaluator=membership).first()
        form = EvaluationForm(request.POST, instance=existing)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.proposal = proposal
            evaluation.evaluator = membership
            evaluation.save()
            messages.success(request, "Avis enregistré.")
        else:
            messages.error(request, "Veuillez sélectionner un avis avant d'enregistrer.")
        return redirect("submissions:evaluator_access", token=str(token))
