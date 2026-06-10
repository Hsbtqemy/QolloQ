import logging
from email.utils import parseaddr

from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.utils import timezone

logger = logging.getLogger(__name__)

from apps.events.models import Membership
from apps.submissions.models import Proposal

from .models import EmailCampaign


def _collect_recipients(campaign):
    """Retourne la liste dédupliquée des adresses email selon l'audience.

    Utilise contact_email pour couvrir les membres avec compte (user.email)
    ET les membres tokenisés sans compte (membership.email).
    """
    event = campaign.event
    emails = set()

    if campaign.audience == EmailCampaign.Audience.ALL_MEMBERS:
        qs = Membership.objects.filter(event=event).select_related("user")
        emails.update(m.contact_email for m in qs if m.contact_email)

    elif campaign.audience == EmailCampaign.Audience.SPEAKERS:
        qs = Membership.objects.filter(
            event=event, role=Membership.Role.SPEAKER
        ).select_related("user")
        emails.update(m.contact_email for m in qs if m.contact_email)

    elif campaign.audience == EmailCampaign.Audience.ACCEPTED:
        emails.update(
            Proposal.objects.filter(event=event, status=Proposal.Status.ACCEPTED)
            .values_list("submitter_email", flat=True)
        )

    elif campaign.audience == EmailCampaign.Audience.COMMITTEE:
        qs = Membership.objects.filter(
            event=event,
            role__in=[Membership.Role.ORGANIZER, Membership.Role.COMMITTEE],
        ).select_related("user")
        emails.update(m.contact_email for m in qs if m.contact_email)

    return list(emails)


def send_campaign(campaign):
    """Envoie la campagne et met à jour sent_at / sent_count. Idempotent si déjà envoyé."""
    if campaign.is_sent:
        return 0

    recipients = _collect_recipients(campaign)
    if not recipients:
        return 0

    _, addr = parseaddr(settings.DEFAULT_FROM_EMAIL)
    from_email = f"{campaign.event.name} <{addr or settings.DEFAULT_FROM_EMAIL}>"

    count = 0
    with get_connection() as conn:
        for email in recipients:
            msg = EmailMessage(
                subject=campaign.subject,
                body=campaign.body,
                from_email=from_email,
                to=[email],
                connection=conn,
            )
            try:
                msg.send()
                count += 1
            except Exception:
                logger.exception("Échec envoi campagne %s à %s", campaign.pk, email)

    campaign.sent_at = timezone.now()
    campaign.sent_count = count
    campaign.save(update_fields=["sent_at", "sent_count"])
    return count
