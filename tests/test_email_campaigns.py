import pytest
from django.utils import timezone

from apps.emails.models import EmailCampaign
from apps.emails.sending import send_campaign

from .factories import (
    EmailCampaignFactory,
    EventFactory,
    MembershipFactory,
    ProposalFactory,
)


# ── Accès vues ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_campaign_list_requires_login(client):
    event = EventFactory()
    response = client.get(f"/evenements/{event.slug}/emails/")
    assert response.status_code == 302


@pytest.mark.django_db
def test_campaign_list_committee_403(client):
    membership = MembershipFactory(role="committee")
    client.force_login(membership.user)
    response = client.get(f"/evenements/{membership.event.slug}/emails/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_campaign_list_organizer_200(client):
    membership = MembershipFactory(role="organizer")
    client.force_login(membership.user)
    response = client.get(f"/evenements/{membership.event.slug}/emails/")
    assert response.status_code == 200


# ── CRUD campagnes ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_campaign_create(client):
    membership = MembershipFactory(role="organizer")
    client.force_login(membership.user)
    response = client.post(
        f"/evenements/{membership.event.slug}/emails/nouveau/",
        {
            "subject": "Objet de test",
            "body": "Corps du message.",
            "audience": EmailCampaign.Audience.ALL_MEMBERS,
        },
    )
    assert response.status_code == 302
    assert membership.event.email_campaigns.filter(subject="Objet de test").exists()


@pytest.mark.django_db
def test_campaign_detail_200(client):
    membership = MembershipFactory(role="organizer")
    campaign = EmailCampaignFactory(event=membership.event)
    client.force_login(membership.user)
    response = client.get(
        f"/evenements/{membership.event.slug}/emails/{campaign.pk}/"
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_campaign_edit_blocked_after_send(client):
    """Une campagne déjà envoyée ne peut plus être modifiée."""
    membership = MembershipFactory(role="organizer")
    campaign = EmailCampaignFactory(
        event=membership.event, sent_at=timezone.now()
    )
    client.force_login(membership.user)
    response = client.get(
        f"/evenements/{membership.event.slug}/emails/{campaign.pk}/modifier/"
    )
    assert response.status_code == 302  # redirigé vers le détail

    response = client.post(
        f"/evenements/{membership.event.slug}/emails/{campaign.pk}/modifier/",
        {"subject": "Tentative", "body": "...", "audience": "all_members"},
    )
    assert response.status_code == 302
    campaign.refresh_from_db()
    assert campaign.subject != "Tentative"


@pytest.mark.django_db
def test_campaign_delete_blocked_after_send(client):
    """Une campagne déjà envoyée ne peut pas être supprimée."""
    membership = MembershipFactory(role="organizer")
    campaign = EmailCampaignFactory(
        event=membership.event, sent_at=timezone.now()
    )
    client.force_login(membership.user)
    client.post(
        f"/evenements/{membership.event.slug}/emails/{campaign.pk}/supprimer/"
    )
    assert EmailCampaign.objects.filter(pk=campaign.pk).exists()


# ── Envoi de campagne ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_campaign_send_to_all_members(mailoutbox):
    """Audience all_members → un email par membre avec adresse."""
    membership = MembershipFactory(role="organizer")
    campaign = EmailCampaignFactory(
        event=membership.event, audience=EmailCampaign.Audience.ALL_MEMBERS
    )
    count = send_campaign(campaign)
    assert count == 1
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == [membership.user.email]


@pytest.mark.django_db
def test_campaign_send_to_accepted_proposals(mailoutbox):
    """Audience accepted → seules les propositions acceptées reçoivent l'email."""
    event = EventFactory()
    ProposalFactory(event=event, status="accepted", submitter_email="accepte@example.com")
    ProposalFactory(event=event, status="submitted", submitter_email="soumis@example.com")
    campaign = EmailCampaignFactory(
        event=event, audience=EmailCampaign.Audience.ACCEPTED
    )
    count = send_campaign(campaign)
    assert count == 1
    assert mailoutbox[0].to == ["accepte@example.com"]


@pytest.mark.django_db
def test_campaign_send_no_recipients(mailoutbox):
    """Aucun destinataire dans l'audience → count 0, aucun email."""
    event = EventFactory()  # pas de membres ni propositions
    campaign = EmailCampaignFactory(
        event=event, audience=EmailCampaign.Audience.SPEAKERS
    )
    count = send_campaign(campaign)
    assert count == 0
    assert len(mailoutbox) == 0


@pytest.mark.django_db
def test_campaign_send_updates_sent_at_and_count(mailoutbox):
    """Après envoi, sent_at est défini et sent_count reflète le nombre réel."""
    membership = MembershipFactory(role="organizer")
    campaign = EmailCampaignFactory(
        event=membership.event, audience=EmailCampaign.Audience.ALL_MEMBERS
    )
    assert campaign.sent_at is None
    send_campaign(campaign)
    campaign.refresh_from_db()
    assert campaign.sent_at is not None
    assert campaign.sent_count == 1


@pytest.mark.django_db
def test_campaign_send_idempotent(mailoutbox):
    """Une campagne déjà envoyée retourne 0 sans renvoyer d'emails."""
    membership = MembershipFactory(role="organizer")
    campaign = EmailCampaignFactory(
        event=membership.event,
        audience=EmailCampaign.Audience.ALL_MEMBERS,
        sent_at=timezone.now(),
        sent_count=1,
    )
    count = send_campaign(campaign)
    assert count == 0
    assert len(mailoutbox) == 0


@pytest.mark.django_db
def test_campaign_send_via_view(client, mailoutbox):
    """L'organisateur peut déclencher l'envoi depuis la vue."""
    membership = MembershipFactory(role="organizer")
    campaign = EmailCampaignFactory(
        event=membership.event, audience=EmailCampaign.Audience.ALL_MEMBERS
    )
    client.force_login(membership.user)
    response = client.post(
        f"/evenements/{membership.event.slug}/emails/{campaign.pk}/envoyer/"
    )
    assert response.status_code == 302
    campaign.refresh_from_db()
    assert campaign.is_sent
