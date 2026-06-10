import logging

from django.conf import settings
from django.urls import reverse

from apps.core.mail import send_template_email
from apps.events.models import Membership

logger = logging.getLogger(__name__)


def send_submission_confirmation(proposal) -> None:
    token_url = settings.SITE_URL + reverse(
        "submissions:token_access", kwargs={"token": str(proposal.token)}
    )
    try:
        send_template_email(
            to=proposal.submitter_email,
            subject=f"Proposition reçue — {proposal.event.name}",
            template_base="submission_confirmation",
            context={
                "event_name": proposal.event.name,
                "proposal_title": proposal.title,
                "token_url": token_url,
                "is_bilingual": proposal.event.is_bilingual,
            },
            event=proposal.event,
        )
    except Exception:
        logger.exception("send_submission_confirmation failed for proposal %s", proposal.pk)


def send_token_reminder(proposal) -> None:
    token_url = settings.SITE_URL + reverse(
        "submissions:token_access", kwargs={"token": str(proposal.token)}
    )
    try:
        send_template_email(
            to=proposal.submitter_email,
            subject=f"Votre lien de suivi — {proposal.event.name}",
            template_base="submission_token_reminder",
            context={
                "event_name": proposal.event.name,
                "proposal_title": proposal.title,
                "token_url": token_url,
                "is_bilingual": proposal.event.is_bilingual,
            },
            event=proposal.event,
        )
    except Exception:
        logger.exception("send_token_reminder failed for proposal %s", proposal.pk)


def send_new_submission_notification(proposal) -> None:
    """Notifie tous les organisateurs de l'événement qu'une nouvelle proposition a été déposée."""
    proposal_url = settings.SITE_URL + reverse(
        "submissions:detail",
        kwargs={"event_slug": proposal.event.slug, "proposal_id": proposal.pk},
    )
    organizers = Membership.objects.filter(
        event=proposal.event,
        role=Membership.Role.ORGANIZER,
    ).select_related("user")
    for membership in organizers:
        email = membership.contact_email
        if not email:
            continue
        try:
            send_template_email(
                to=email,
                subject=f"Nouvelle soumission — {proposal.event.name}",
                template_base="new_submission_notification",
                context={
                    "event": proposal.event,
                    "proposal": proposal,
                    "proposal_url": proposal_url,
                },
                event=proposal.event,
            )
        except Exception:
            logger.exception(
                "send_new_submission_notification failed for proposal %s to %s",
                proposal.pk, email,
            )
