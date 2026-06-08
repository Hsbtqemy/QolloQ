from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from apps.core.mixins import EventMemberRequiredMixin, OrganizerRequiredMixin
from apps.documents.views import annotate_documents

from .forms import EventForm
from .models import Event, Membership


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
        documents = list(self.event.documents.select_related("uploaded_by").all())
        annotate_documents(documents, event_slug)
        return render(request, "events/detail.html", {
            "event": self.event,
            "membership": self.membership,
            "documents": documents,
            "is_editable": self.membership.is_organizer,
            "doc_create_url": reverse("documents:create", kwargs={"event_slug": event_slug}),
        })


class EventSettingsView(OrganizerRequiredMixin, View):
    def get(self, request, event_slug):
        return render(request, "events/settings.html", {
            "event": self.event,
            "form": EventForm(instance=self.event),
        })

    def post(self, request, event_slug):
        form = EventForm(request.POST, instance=self.event)
        if form.is_valid():
            form.save()
            return redirect("events:detail", event_slug=self.event.slug)
        return render(request, "events/settings.html", {"event": self.event, "form": form})
