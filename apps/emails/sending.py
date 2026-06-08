from email.utils import parseaddr

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from apps.events.models import Membership
from apps.submissions.models import Proposal

from .models import EmailCampaign


def _collect_recipients(campaign):
    """Retourne la liste dédupliquée des adresses email selon l'audience."""
    event = campaign.event
    emails = set()

    if campaign.audience == EmailCampaign.Audience.ALL_MEMBERS:
        emails.update(
            Membership.objects.filter(event=event)
            .values_list("user__email", flat=True)
        )

    elif campaign.audience == EmailCampaign.Audience.SPEAKERS:
        emails.update(
            Membership.objects.filter(event=event, role=Membership.Role.SPEAKER)
            .values_list("user__email", flat=True)
        )

    elif campaign.audience == EmailCampaign.Audience.ACCEPTED:
        emails.update(
            Proposal.objects.filter(event=event, status=Proposal.Status.ACCEPTED)
            .values_list("submitter_email", flat=True)
        )

    elif campaign.audience == EmailCampaign.Audience.COMMITTEE:
        emails.update(
            Membership.objects.filter(
                event=event,
                role__in=[Membership.Role.ORGANIZER, Membership.Role.COMMITTEE],
            )
            .values_list("user__email", flat=True)
        )

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
    for email in recipients:
        msg = EmailMessage(
            subject=campaign.subject,
            body=campaign.body,
            from_email=from_email,
            to=[email],
        )
        msg.send()
        count += 1

    campaign.sent_at = timezone.now()
    campaign.sent_count = count
    campaign.save(update_fields=["sent_at", "sent_count"])
    return count
