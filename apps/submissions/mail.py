import logging

from django.conf import settings
from django.urls import reverse

from apps.core.mail import send_template_email

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
