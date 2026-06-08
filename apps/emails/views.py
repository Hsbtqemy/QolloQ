from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.core.mixins import OrganizerRequiredMixin

from .forms import EmailCampaignForm
from .models import EmailCampaign
from .sending import send_campaign


class CampaignListView(OrganizerRequiredMixin, View):
    def get(self, request, event_slug):
        campaigns = self.event.email_campaigns.order_by("-created_at")
        return render(
            request,
            "emails/campaign_list.html",
            {"event": self.event, "membership": self.membership, "campaigns": campaigns},
        )


class CampaignCreateView(OrganizerRequiredMixin, View):
    def get(self, request, event_slug):
        form = EmailCampaignForm()
        return render(
            request,
            "emails/campaign_form.html",
            {"event": self.event, "membership": self.membership, "form": form},
        )

    def post(self, request, event_slug):
        form = EmailCampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.event = self.event
            campaign.save()
            messages.success(request, "Campagne créée.")
            return redirect("emails:campaign_detail", event_slug=event_slug, pk=campaign.pk)
        return render(
            request,
            "emails/campaign_form.html",
            {"event": self.event, "membership": self.membership, "form": form},
        )


class CampaignDetailView(OrganizerRequiredMixin, View):
    def get(self, request, event_slug, pk):
        campaign = get_object_or_404(EmailCampaign, pk=pk, event=self.event)
        return render(
            request,
            "emails/campaign_detail.html",
            {"event": self.event, "membership": self.membership, "campaign": campaign},
        )


class CampaignEditView(OrganizerRequiredMixin, View):
    def get(self, request, event_slug, pk):
        campaign = get_object_or_404(EmailCampaign, pk=pk, event=self.event)
        if campaign.is_sent:
            messages.error(request, "Cette campagne a déjà été envoyée.")
            return redirect("emails:campaign_detail", event_slug=event_slug, pk=pk)
        form = EmailCampaignForm(instance=campaign)
        return render(
            request,
            "emails/campaign_form.html",
            {"event": self.event, "membership": self.membership, "form": form, "campaign": campaign},
        )

    def post(self, request, event_slug, pk):
        campaign = get_object_or_404(EmailCampaign, pk=pk, event=self.event)
        if campaign.is_sent:
            messages.error(request, "Cette campagne a déjà été envoyée.")
            return redirect("emails:campaign_detail", event_slug=event_slug, pk=pk)
        form = EmailCampaignForm(request.POST, instance=campaign)
        if form.is_valid():
            form.save()
            messages.success(request, "Campagne mise à jour.")
            return redirect("emails:campaign_detail", event_slug=event_slug, pk=pk)
        return render(
            request,
            "emails/campaign_form.html",
            {"event": self.event, "membership": self.membership, "form": form, "campaign": campaign},
        )


class CampaignDeleteView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, pk):
        campaign = get_object_or_404(EmailCampaign, pk=pk, event=self.event)
        if campaign.is_sent:
            messages.error(request, "Impossible de supprimer une campagne déjà envoyée.")
            return redirect("emails:campaign_detail", event_slug=event_slug, pk=pk)
        campaign.hard_delete()
        messages.success(request, "Campagne supprimée.")
        return redirect("emails:campaign_list", event_slug=event_slug)


class CampaignSendView(OrganizerRequiredMixin, View):
    """Envoi effectif de la campagne — POST uniquement, confirmation côté template."""

    def post(self, request, event_slug, pk):
        campaign = get_object_or_404(EmailCampaign, pk=pk, event=self.event)
        if campaign.is_sent:
            messages.warning(request, "Cette campagne a déjà été envoyée.")
            return redirect("emails:campaign_detail", event_slug=event_slug, pk=pk)
        count = send_campaign(campaign)
        if count == 0:
            messages.warning(request, "Aucun destinataire trouvé pour cette audience.")
        else:
            messages.success(request, f"Campagne envoyée à {count} destinataire(s).")
        return redirect("emails:campaign_detail", event_slug=event_slug, pk=pk)
