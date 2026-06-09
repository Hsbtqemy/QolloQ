import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models as db_models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from apps.core.mixins import EventMemberRequiredMixin, OrganizerRequiredMixin
from apps.documents.views import annotate_documents
from apps.submissions.models import Proposal

from .forms import EventForm, EventPublicPageForm, MemberAddForm
from .mail import send_member_invitation
from .models import Event, KeyDate, Membership, Task

logger = logging.getLogger(__name__)


class HomeView(LoginRequiredMixin, View):
    def get(self, request):
        events = (
            Event.objects.filter(memberships__user=request.user)
            .prefetch_related("memberships__user")
            .order_by("-start_date")
            .distinct()
        )
        return render(request, "events/home.html", {"events": events})


class EventCreateView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, "events/create.html", {"form": EventForm()})

    def post(self, request):
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.created_by = request.user
            event.save()
            Membership.objects.create(user=request.user, event=event, role=Membership.Role.ORGANIZER)
            return redirect("events:detail", event_slug=event.slug)
        return render(request, "events/create.html", {"form": form})


class EventDetailView(EventMemberRequiredMixin, View):
    def get(self, request, event_slug):
        today = timezone.localdate()
        proposals = self.event.proposals.all()
        accepted = proposals.filter(status=Proposal.Status.ACCEPTED)
        stats = {
            "total":     proposals.count(),
            "accepted":  accepted.count(),
            "confirmed": accepted.filter(attendance=Proposal.Attendance.CONFIRMED).count(),
            "cancelled": accepted.filter(attendance=Proposal.Attendance.CANCELLED).count(),
        }
        documents = list(self.event.documents.select_related("uploaded_by").all())
        annotate_documents(documents, event_slug)
        return render(request, "events/detail.html", {
            "event":      self.event,
            "membership": self.membership,
            "documents":  documents,
            "is_editable": self.membership.is_organizer,
            "doc_create_url": reverse("documents:create", kwargs={"event_slug": event_slug}),
            "stats":      stats,
            "key_dates":  self.event.key_dates.all(),
            "tasks":      self.event.tasks.all(),
            "today":      today,
            "pending_tasks": self.event.tasks.filter(done=False).count(),
        })


class KeyDateCreateView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug):
        label = request.POST.get("label", "").strip()
        date_str = request.POST.get("date", "").strip()
        if label and date_str:
            try:
                from datetime import date
                KeyDate.objects.create(event=self.event, label=label, date=date.fromisoformat(date_str))
            except ValueError:
                pass
        return redirect("events:detail", event_slug=event_slug)


class KeyDateDeleteView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, pk):
        KeyDate.objects.filter(event=self.event, pk=pk).delete()
        return redirect("events:detail", event_slug=event_slug)


class TaskCreateView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug):
        title = request.POST.get("title", "").strip()
        due_str = request.POST.get("due_date", "").strip()
        if title:
            due = None
            if due_str:
                try:
                    from datetime import date
                    due = date.fromisoformat(due_str)
                except ValueError:
                    pass
            max_order = self.event.tasks.aggregate(m=db_models.Max("order"))["m"] or 0
            Task.objects.create(event=self.event, title=title, due_date=due, order=max_order + 1)
        return redirect("events:detail", event_slug=event_slug)


class TaskToggleView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, pk):
        task = get_object_or_404(Task, event=self.event, pk=pk)
        task.done = not task.done
        task.save(update_fields=["done", "updated_at"])
        return JsonResponse({"done": task.done})


class TaskDeleteView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, pk):
        Task.objects.filter(event=self.event, pk=pk).delete()
        return redirect("events:detail", event_slug=event_slug)


class EventSettingsView(OrganizerRequiredMixin, View):
    def get(self, request, event_slug):
        return render(request, "events/settings.html", {
            "event": self.event,
            "membership": self.membership,
            "form": EventForm(instance=self.event),
        })

    def post(self, request, event_slug):
        form = EventForm(request.POST, instance=self.event)
        if form.is_valid():
            form.save()
            return redirect("events:detail", event_slug=self.event.slug)
        return render(request, "events/settings.html", {
            "event": self.event,
            "membership": self.membership,
            "form": form,
        })


class MemberListView(OrganizerRequiredMixin, View):
    def get(self, request, event_slug):
        members = (
            self.event.memberships
            .select_related("user")
            .order_by("role", "user__last_name")
        )
        return render(request, "events/members.html", {
            "event": self.event,
            "membership": self.membership,
            "members": members,
            "form": MemberAddForm(event=self.event),
            "role_choices": Membership.Role.choices,
        })


class MemberAddView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug):
        form = MemberAddForm(request.POST, event=self.event)
        if form.is_valid():
            role = form.cleaned_data["role"]
            email = form.cleaned_data["email"]

            if form.is_new_user:
                User = get_user_model()
                user = User.objects.create_user(
                    email=email,
                    password=None,
                    first_name=form.cleaned_data.get("first_name", ""),
                    last_name=form.cleaned_data.get("last_name", ""),
                    must_change_password=True,
                )
                user.set_unusable_password()
                user.save(update_fields=["password"])
            else:
                user = form.cleaned_user

            Membership.objects.create(user=user, event=self.event, role=role)

            invitation_url = self._build_invitation_url(request, user)
            try:
                send_member_invitation(user, self.event, role, invitation_url)
            except Exception:
                logger.exception("send_member_invitation failed for %s on event %s", email, self.event.pk)

            name = user.get_full_name() or email
            if form.is_new_user:
                messages.success(request, f"Compte créé et invitation envoyée à {email}.")
            else:
                messages.success(request, f"{name} ajouté·e — invitation envoyée.")
            return redirect("events:members", event_slug=event_slug)

        members = (
            self.event.memberships
            .select_related("user")
            .order_by("role", "user__last_name")
        )
        return render(request, "events/members.html", {
            "event": self.event,
            "membership": self.membership,
            "members": members,
            "form": form,
            "role_choices": Membership.Role.choices,
        })

    def _build_invitation_url(self, request, user):
        if user.has_usable_password():
            return request.build_absolute_uri(
                reverse("events:detail", kwargs={"event_slug": self.event.slug})
            )
        try:
            from allauth.account.adapter import get_adapter
            from allauth.account.app_settings import app_settings
            from allauth.account.utils import user_pk_to_url_str

            token_generator = app_settings.PASSWORD_RESET_TOKEN_GENERATOR()
            uid = user_pk_to_url_str(user)
            key = f"{uid}-{token_generator.make_token(user)}"
            adapter = get_adapter(request)
            return adapter.get_reset_password_from_key_url(key)
        except Exception:
            logger.exception("Could not build invitation URL for user %s", user.pk)
            return request.build_absolute_uri(reverse("account_login"))


class MemberUpdateView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, membership_id):
        member = get_object_or_404(Membership, pk=membership_id, event=self.event)
        new_role = request.POST.get("role")
        if new_role not in Membership.Role.values:
            messages.error(request, "Rôle invalide.")
            return redirect("events:members", event_slug=event_slug)
        # Empêche de rétrograder le dernier organisateur
        if member.is_organizer and new_role != Membership.Role.ORGANIZER:
            organizer_count = self.event.memberships.filter(role=Membership.Role.ORGANIZER).count()
            if organizer_count <= 1:
                messages.error(request, "Impossible : il doit rester au moins un organisateur.")
                return redirect("events:members", event_slug=event_slug)
        member.role = new_role
        member.save(update_fields=["role", "updated_at"])
        messages.success(request, "Rôle mis à jour.")
        return redirect("events:members", event_slug=event_slug)


class MemberRemoveView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, membership_id):
        member = get_object_or_404(Membership, pk=membership_id, event=self.event)
        if member.is_organizer:
            organizer_count = self.event.memberships.filter(role=Membership.Role.ORGANIZER).count()
            if organizer_count <= 1:
                messages.error(request, "Impossible : il doit rester au moins un organisateur.")
                return redirect("events:members", event_slug=event_slug)
        name = member.user.get_full_name() or member.user.email
        member.delete()
        messages.success(request, f"{name} retiré·e de l'événement.")
        return redirect("events:members", event_slug=event_slug)


class EventPublicSettingsView(OrganizerRequiredMixin, View):
    def get(self, request, event_slug):
        return render(request, "events/public_settings.html", {
            "event": self.event,
            "membership": self.membership,
            "form": EventPublicPageForm(instance=self.event),
        })

    def post(self, request, event_slug):
        form = EventPublicPageForm(request.POST, request.FILES, instance=self.event)
        if form.is_valid():
            form.save()
            messages.success(request, "Contenu enregistré.")
            return redirect("events:public_settings", event_slug=event_slug)
        return render(request, "events/public_settings.html", {
            "event": self.event,
            "membership": self.membership,
            "form": form,
        })
