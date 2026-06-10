import pytest
from django.conf import settings

from apps.core.mail import send_template_email
from apps.emails.models import EmailTemplate

from .factories import EventFactory


# ── send_template_email — template DB ─────────────────────────────────────────

@pytest.mark.django_db
def test_send_template_email_uses_db_subject(mailoutbox):
    """Le sujet est rendu depuis le template DB (avec variables contexte)."""
    EmailTemplate.objects.filter(key="submission_confirmation").update(
        subject_fr="Confirmation pour {{ event_name }}"
    )

    send_template_email(
        to="test@example.com",
        subject="Sujet ignoré",
        template_base="submission_confirmation",
        context={
            "event_name": "MonColloque",
            "proposal_title": "Titre",
            "token_url": "http://example.com/token/",
            "is_bilingual": False,
        },
    )

    assert len(mailoutbox) == 1
    assert mailoutbox[0].subject == "Confirmation pour MonColloque"


@pytest.mark.django_db
def test_send_template_email_injects_body_from_db(mailoutbox):
    """Le corps (email_body_fr) est rendu depuis la DB et apparaît dans le TXT."""
    EmailTemplate.objects.filter(key="submission_confirmation").update(
        body_fr="Votre proposition {{ proposal_title }} a bien été reçue."
    )

    send_template_email(
        to="test@example.com",
        subject="Test",
        template_base="submission_confirmation",
        context={
            "event_name": "Colloque",
            "proposal_title": "Ma communication",
            "token_url": "http://example.com/token/",
            "is_bilingual": False,
        },
    )

    assert len(mailoutbox) == 1
    assert "Ma communication" in mailoutbox[0].body


@pytest.mark.django_db
def test_send_template_email_fallback_when_template_missing(mailoutbox):
    """Sans template DB, l'email part quand même avec le sujet passé en argument."""
    EmailTemplate.objects.filter(key="submission_confirmation").delete()

    send_template_email(
        to="test@example.com",
        subject="Sujet de secours",
        template_base="submission_confirmation",
        context={
            "event_name": "Colloque",
            "proposal_title": "Titre",
            "token_url": "http://example.com/token/",
            "is_bilingual": False,
        },
    )

    assert len(mailoutbox) == 1
    assert mailoutbox[0].subject == "Sujet de secours"
    assert mailoutbox[0].to == ["test@example.com"]


# ── Nom d'expéditeur (from_name) ──────────────────────────────────────────────

@pytest.mark.django_db
def test_from_name_appears_in_from_header(mailoutbox):
    """event.from_name est utilisé comme nom d'expéditeur dans le header From."""
    event = EventFactory(from_name="Equipe organisatrice")

    send_template_email(
        to="test@example.com",
        subject="Test",
        template_base="submission_confirmation",
        context={
            "event_name": event.name,
            "proposal_title": "Titre",
            "token_url": "http://example.com/token/",
            "is_bilingual": False,
        },
        event=event,
    )

    assert len(mailoutbox) == 1
    assert "Equipe organisatrice" in mailoutbox[0].from_email


@pytest.mark.django_db
def test_from_name_falls_back_to_event_name(mailoutbox):
    """Sans from_name, le nom de l'événement est utilisé comme expéditeur."""
    event = EventFactory(from_name="")

    send_template_email(
        to="test@example.com",
        subject="Test",
        template_base="submission_confirmation",
        context={
            "event_name": event.name,
            "proposal_title": "Titre",
            "token_url": "http://example.com/token/",
            "is_bilingual": False,
        },
        event=event,
    )

    assert len(mailoutbox) == 1
    assert event.name in mailoutbox[0].from_email


@pytest.mark.django_db
def test_no_event_uses_default_from_email(mailoutbox):
    """Sans event, le DEFAULT_FROM_EMAIL est utilisé tel quel."""
    send_template_email(
        to="test@example.com",
        subject="Test",
        template_base="submission_confirmation",
        context={
            "event_name": "Colloque",
            "proposal_title": "Titre",
            "token_url": "http://example.com/token/",
            "is_bilingual": False,
        },
    )

    assert len(mailoutbox) == 1
    assert mailoutbox[0].from_email == settings.DEFAULT_FROM_EMAIL
