import json

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.core.mixins import CommitteeRequiredMixin, OrganizerRequiredMixin
from apps.events.models import Event, Membership

from .forms import (
    AuthorFormSet,
    EvaluationForm,
    OrganizerProposalForm,
    PublicProposalForm,
    ResendTokenForm,
)
from .mail import send_submission_confirmation, send_token_reminder
from .models import Evaluation, Proposal


# ── Vues publiques (sans compte) ─────────────────────────────────────────────

class PublicSubmitView(View):
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
            "form": PublicProposalForm(),
            "author_formset": AuthorFormSet(),
        })

    def post(self, request, event_slug):
        event = self._get_open_event(event_slug)
        form = PublicProposalForm(request.POST)
        author_formset = AuthorFormSet(request.POST)
        if form.is_valid() and author_formset.is_valid():
            proposal = form.save(commit=False)
            proposal.event = event
            proposal.save()
            author_formset.instance = proposal
            author_formset.save()
            send_submission_confirmation(proposal)
            return redirect("submissions:submitted", token=str(proposal.token))
        return render(request, "submissions/public_submit.html", {
            "event": event,
            "form": form,
            "author_formset": author_formset,
        })


class SubmissionSubmittedView(View):
    """Page de confirmation après soumission."""

    def get(self, request, token):
        proposal = get_object_or_404(Proposal, token=token)
        return render(request, "submissions/submitted.html", {"proposal": proposal})


class TokenAccessView(View):
    """Accès soumissionnaire via lien tokenisé : consulter, modifier, retirer."""

    def _is_still_editable(self, proposal):
        if not proposal.is_editable:
            return False
        deadline = proposal.event.submission_deadline
        if deadline and deadline < timezone.now():
            return False
        return True

    def get(self, request, token):
        proposal = get_object_or_404(Proposal, token=token)
        editable = self._is_still_editable(proposal)
        return render(request, "submissions/token_access.html", {
            "proposal": proposal,
            "editable": editable,
            "form": PublicProposalForm(instance=proposal) if editable else None,
            "author_formset": AuthorFormSet(instance=proposal) if editable else None,
        })

    def post(self, request, token):
        proposal = get_object_or_404(Proposal, token=token)
        if not self._is_still_editable(proposal):
            raise PermissionDenied

        action = request.POST.get("action")
        if action == "withdraw":
            event = proposal.event  # sauvegardé avant suppression
            proposal.hard_delete()
            return render(request, "submissions/withdrawn.html", {"event": event})

        form = PublicProposalForm(request.POST, instance=proposal)
        author_formset = AuthorFormSet(request.POST, instance=proposal)
        if form.is_valid() and author_formset.is_valid():
            form.save()
            author_formset.save()
            messages.success(request, "Votre proposition a été mise à jour.")
            return redirect("submissions:token_access", token=token)
        return render(request, "submissions/token_access.html", {
            "proposal": proposal,
            "editable": True,
            "form": form,
            "author_formset": author_formset,
        })


class ResendTokenView(View):
    """Renvoi du lien tokenisé sur saisie de l'email."""

    def get(self, request, event_slug):
        event = get_object_or_404(Event, slug=event_slug)
        return render(request, "submissions/resend_token.html", {
            "event": event,
            "form": ResendTokenForm(),
        })

    def post(self, request, event_slug):
        event = get_object_or_404(Event, slug=event_slug)
        form = ResendTokenForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            for proposal in Proposal.objects.filter(event=event, submitter_email=email):
                send_token_reminder(proposal)
            # Réponse neutre même si aucune proposition trouvée (anti-énumération)
            return render(request, "submissions/resend_token_sent.html", {"event": event})
        return render(request, "submissions/resend_token.html", {"event": event, "form": form})


# ── Vues organisateur / comité ────────────────────────────────────────────────

class ProposalListView(CommitteeRequiredMixin, View):
    def get(self, request, event_slug):
        proposals = (
            Proposal.objects.filter(event=self.event)
            .prefetch_related("authors", "evaluations")
            .order_by("-created_at")
        )
        return render(request, "submissions/organizer/list.html", {
            "event": self.event,
            "membership": self.membership,
            "proposals": proposals,
            "status_choices": Proposal.Status.choices,
        })


class ProposalDetailView(CommitteeRequiredMixin, View):
    def get(self, request, event_slug, proposal_id):
        proposal = get_object_or_404(Proposal, pk=proposal_id, event=self.event)
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
            "organizer_form": OrganizerProposalForm(instance=proposal) if self.membership.is_organizer else None,
        })

    def _get_visible_evaluations(self, proposal):
        # Les organisateurs voient toujours tout
        if self.membership.is_organizer:
            return proposal.evaluations.select_related("evaluator__user").all()

        # Pour le comité : respect du paramètre eval_visibility
        own_exists = Evaluation.objects.filter(
            proposal=proposal, evaluator=self.membership
        ).exists()
        if self.event.eval_visibility == Event.EvalVisibility.AFTER_OWN and not own_exists:
            return Evaluation.objects.none()

        # Anonymat inter-évaluateurs
        if self.event.eval_anonymous:
            return proposal.evaluations.all()  # template masque les noms
        return proposal.evaluations.select_related("evaluator__user").all()


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
        proposal = get_object_or_404(Proposal, pk=proposal_id, event=self.event)
        form = OrganizerProposalForm(request.POST, instance=proposal)
        author_formset = AuthorFormSet(request.POST, instance=proposal)
        if form.is_valid() and author_formset.is_valid():
            form.save()
            author_formset.save()
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
            "form": OrganizerProposalForm(),
            "author_formset": AuthorFormSet(),
        })

    def post(self, request, event_slug):
        form = OrganizerProposalForm(request.POST)
        author_formset = AuthorFormSet(request.POST)
        if form.is_valid() and author_formset.is_valid():
            proposal = form.save(commit=False)
            proposal.event = self.event
            proposal.save()
            author_formset.instance = proposal
            author_formset.save()
            messages.success(request, "Proposition créée.")
            return redirect("submissions:detail", event_slug=event_slug, proposal_id=proposal.pk)
        return render(request, "submissions/organizer/create.html", {
            "event": self.event,
            "form": form,
            "author_formset": author_formset,
        })
