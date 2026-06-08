import json
from collections import defaultdict
from datetime import timedelta

from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views import View

from apps.core.mixins import CommitteeRequiredMixin, OrganizerRequiredMixin
from apps.submissions.models import Proposal

from .forms import AnnexEventForm, CommunicationForm, SessionForm
from .models import AnnexEvent, Communication, Session


def _event_days(event):
    """Retourne la liste des jours couverts par l'événement."""
    days = []
    current = event.start_date
    while current <= event.end_date:
        days.append(current)
        current += timedelta(days=1)
    return days


def _build_programme_context(event):
    """Construit le contexte commun aux vues programme (organisateur et lecture)."""
    days = _event_days(event)
    sessions_by_day = defaultdict(list)
    for session in (
        Session.objects.filter(event=event)
        .prefetch_related("communications__proposal")
        .order_by("date", "start_time", "order")
    ):
        sessions_by_day[session.date].append(session)

    annex_by_day = defaultdict(list)
    for item in AnnexEvent.objects.filter(event=event).order_by("date", "start_time"):
        annex_by_day[item.date].append(item)

    # Vue par jour : sessions + annexes mélangés, triés par heure de début
    programme = []
    for day in days:
        items = [
            {"kind": "session", "obj": s, "start": s.start_time, "end": s.end_time}
            for s in sessions_by_day[day]
        ] + [
            {"kind": "annex", "obj": a, "start": a.start_time, "end": a.end_time}
            for a in annex_by_day[day]
        ]
        items.sort(key=lambda x: x["start"])
        programme.append({"date": day, "items": items})

    return {
        "days": days,
        "programme": programme,
        "sessions_by_day": dict(sessions_by_day),
    }


# ── Vues organisateur ─────────────────────────────────────────────────────────

class ProgrammeView(OrganizerRequiredMixin, View):
    def get(self, request, event_slug):
        ctx = _build_programme_context(self.event)
        accepted_proposals = Proposal.objects.filter(
            event=self.event,
            status=Proposal.Status.ACCEPTED,
        ).exclude(communication__isnull=False)
        return render(request, "programme/organizer/programme.html", {
            "event": self.event,
            "session_form": SessionForm(event=self.event),
            "annex_form": AnnexEventForm(event=self.event),
            "comm_form": CommunicationForm(event=self.event),
            "accepted_proposals": accepted_proposals,
            **ctx,
        })


class SessionCreateView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug):
        form = SessionForm(request.POST, event=self.event)
        if form.is_valid():
            session = form.save(commit=False)
            session.event = self.event
            # ordre = dernier + 1 pour ce jour
            last = (
                Session.objects.filter(event=self.event, date=session.date)
                .order_by("-order")
                .values_list("order", flat=True)
                .first()
            )
            session.order = (last or 0) + 1
            session.save()
            messages.success(request, "Session créée.")
        else:
            messages.error(request, "Erreur dans le formulaire de session.")
        return redirect("programme:programme", event_slug=event_slug)


class SessionUpdateView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, session_id):
        session = get_object_or_404(Session, pk=session_id, event=self.event)
        form = SessionForm(request.POST, instance=session, event=self.event)
        if form.is_valid():
            form.save()
            messages.success(request, "Session mise à jour.")
        return redirect("programme:programme", event_slug=event_slug)


class SessionDeleteView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, session_id):
        session = get_object_or_404(Session, pk=session_id, event=self.event)
        session.delete()
        messages.success(request, "Session supprimée.")
        return redirect("programme:programme", event_slug=event_slug)


class SessionReorderView(OrganizerRequiredMixin, View):
    """POST JSON [{id, order}] — réordonne les sessions d'un même jour."""

    def post(self, request, event_slug):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "JSON invalide."}, status=400)
        if not isinstance(data, list) or not data:
            return JsonResponse({"error": "Format invalide."}, status=400)
        try:
            order_map = {int(item["id"]): int(item["order"]) for item in data}
        except (KeyError, ValueError, TypeError):
            return JsonResponse({"error": "Format invalide."}, status=400)

        orders = list(order_map.values())
        if len(set(orders)) != len(orders) or any(v <= 0 for v in orders):
            return JsonResponse({"error": "Ordres invalides."}, status=400)

        sessions = list(Session.objects.filter(event=self.event, pk__in=order_map.keys()))
        if set(s.pk for s in sessions) != set(order_map.keys()):
            return JsonResponse({"error": "Sessions introuvables."}, status=400)

        now = timezone.now()
        for session in sessions:
            session.order = order_map[session.pk]
            session.updated_at = now
        Session.objects.bulk_update(sessions, ["order", "updated_at"])
        return JsonResponse({"ok": True})


class CommunicationCreateView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, session_id):
        session = get_object_or_404(Session, pk=session_id, event=self.event)
        form = CommunicationForm(request.POST, event=self.event)
        if form.is_valid():
            comm = form.save(commit=False)
            comm.session = session
            last = (
                Communication.objects.filter(session=session)
                .order_by("-order")
                .values_list("order", flat=True)
                .first()
            )
            comm.order = (last or 0) + 1
            comm.save()
            messages.success(request, "Communication ajoutée.")
        else:
            messages.error(request, "Erreur dans le formulaire.")
        return redirect("programme:programme", event_slug=event_slug)


class CommunicationUpdateView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, comm_id):
        comm = get_object_or_404(Communication, pk=comm_id, session__event=self.event)
        form = CommunicationForm(request.POST, instance=comm, event=self.event)
        if form.is_valid():
            form.save()
            messages.success(request, "Communication mise à jour.")
        return redirect("programme:programme", event_slug=event_slug)


class CommunicationDeleteView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, comm_id):
        comm = get_object_or_404(Communication, pk=comm_id, session__event=self.event)
        comm.delete()
        messages.success(request, "Communication supprimée.")
        return redirect("programme:programme", event_slug=event_slug)


class CommunicationReorderView(OrganizerRequiredMixin, View):
    """POST JSON [{id, order, session_id}] — réordonne et déplace entre sessions."""

    def post(self, request, event_slug):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "JSON invalide."}, status=400)
        if not isinstance(data, list) or not data:
            return JsonResponse({"error": "Format invalide."}, status=400)
        try:
            updates = [
                {"id": int(item["id"]), "order": int(item["order"]), "session_id": int(item["session_id"])}
                for item in data
            ]
        except (KeyError, ValueError, TypeError):
            return JsonResponse({"error": "Format invalide."}, status=400)

        comm_ids = [u["id"] for u in updates]
        session_ids = {u["session_id"] for u in updates}

        # Vérifie que toutes les sessions appartiennent à cet événement
        valid_sessions = set(
            Session.objects.filter(event=self.event, pk__in=session_ids).values_list("pk", flat=True)
        )
        if valid_sessions != session_ids:
            return JsonResponse({"error": "Sessions introuvables."}, status=400)

        comms = {c.pk: c for c in Communication.objects.filter(pk__in=comm_ids, session__event=self.event)}
        if set(comms.keys()) != set(comm_ids):
            return JsonResponse({"error": "Communications introuvables."}, status=400)

        # Vérifie l'unicité des ordres par session
        orders_by_session = defaultdict(list)
        for u in updates:
            orders_by_session[u["session_id"]].append(u["order"])
        for session_orders in orders_by_session.values():
            if len(set(session_orders)) != len(session_orders) or any(v <= 0 for v in session_orders):
                return JsonResponse({"error": "Ordres invalides dans une session."}, status=400)

        for u in updates:
            comm = comms[u["id"]]
            comm.session_id = u["session_id"]
            comm.order = u["order"]
        Communication.objects.bulk_update(list(comms.values()), ["session_id", "order"])
        return JsonResponse({"ok": True})


class AnnexEventCreateView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug):
        form = AnnexEventForm(request.POST, event=self.event)
        if form.is_valid():
            annex = form.save(commit=False)
            annex.event = self.event
            annex.save()
            messages.success(request, "Événement annexe ajouté.")
        else:
            messages.error(request, "Erreur dans le formulaire.")
        return redirect("programme:programme", event_slug=event_slug)


class AnnexEventUpdateView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, annex_id):
        annex = get_object_or_404(AnnexEvent, pk=annex_id, event=self.event)
        form = AnnexEventForm(request.POST, instance=annex, event=self.event)
        if form.is_valid():
            form.save()
            messages.success(request, "Événement annexe mis à jour.")
        return redirect("programme:programme", event_slug=event_slug)


class AnnexEventDeleteView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, annex_id):
        annex = get_object_or_404(AnnexEvent, pk=annex_id, event=self.event)
        annex.delete()
        messages.success(request, "Événement annexe supprimé.")
        return redirect("programme:programme", event_slug=event_slug)


# ── Export PDF ───────────────────────────────────────────────────────────────

class ProgrammePdfView(CommitteeRequiredMixin, View):
    def get(self, request, event_slug):
        from weasyprint import HTML
        ctx = _build_programme_context(self.event)
        html = render_to_string(
            "programme/programme_pdf.html",
            {"event": self.event, **ctx},
        )
        pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="programme-{self.event.slug}.pdf"'
        )
        return response


# ── Vue calendrier (lecture) ──────────────────────────────────────────────────

class CalendarView(CommitteeRequiredMixin, View):
    """Grille calendrier CSS pure — vue édition pour l'organisateur,
    lecture pour les autres membres."""

    def get(self, request, event_slug):
        ctx = _build_programme_context(self.event)
        # grid_start/grid_end calculés depuis les données déjà chargées dans ctx
        times = [
            item[key]
            for day_data in ctx["programme"]
            for item in day_data["items"]
            for key in ("start", "end")
        ]
        grid_start = min(times).replace(minute=0, second=0) if times else None
        grid_end = max(times) if times else None
        return render(request, "programme/calendar.html", {
            "event": self.event,
            "membership": self.membership,
            "grid_start": grid_start,
            "grid_end": grid_end,
            **ctx,
        })
