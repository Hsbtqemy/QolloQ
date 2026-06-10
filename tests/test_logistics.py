import uuid

import pytest

from .factories import (
    EventFactory,
    LogisticsFormFactory,
    LogisticsResponseFactory,
    MembershipFactory,
)


# ── Accès vues organisateur ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_logistics_index_requires_login(client):
    event = EventFactory()
    response = client.get(f"/evenements/{event.slug}/logistique/")
    assert response.status_code == 302


@pytest.mark.django_db
def test_logistics_index_committee_403(client):
    membership = MembershipFactory(role="committee")
    client.force_login(membership.user)
    response = client.get(f"/evenements/{membership.event.slug}/logistique/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_logistics_index_organizer_200(client):
    membership = MembershipFactory(role="organizer")
    client.force_login(membership.user)
    response = client.get(f"/evenements/{membership.event.slug}/logistique/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_response_list_organizer_200(client):
    membership = MembershipFactory(role="organizer")
    lf = LogisticsFormFactory(event=membership.event)
    client.force_login(membership.user)
    response = client.get(
        f"/evenements/{membership.event.slug}/logistique/{lf.pk}/reponses/"
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_response_list_committee_200(client):
    """Le comité peut consulter les réponses logistiques (CommitteeRequiredMixin)."""
    membership = MembershipFactory(role="committee")
    lf = LogisticsFormFactory(event=membership.event)
    client.force_login(membership.user)
    response = client.get(
        f"/evenements/{membership.event.slug}/logistique/{lf.pk}/reponses/"
    )
    assert response.status_code == 200


# ── Formulaire public (accès tokenisé) ───────────────────────────────────────

@pytest.mark.django_db
def test_public_respond_get_200(client):
    lf = LogisticsFormFactory(is_open=True)
    lr = LogisticsResponseFactory(form=lf)
    response = client.get(f"/logistique/{lr.token}/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_public_respond_get_404_unknown_token(client):
    response = client.get(f"/logistique/{uuid.uuid4()}/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_public_respond_post_marks_complete(client):
    """POST sur un formulaire sans champ obligatoire marque la réponse comme complète."""
    lf = LogisticsFormFactory(is_open=True)
    lr = LogisticsResponseFactory(form=lf)
    response = client.post(f"/logistique/{lr.token}/", {})
    assert response.status_code == 302
    lr.refresh_from_db()
    assert lr.is_complete is True


@pytest.mark.django_db
def test_public_respond_post_closed_403(client):
    """POST sur un formulaire fermé retourne 403."""
    lf = LogisticsFormFactory(is_open=False)
    lr = LogisticsResponseFactory(form=lf)
    response = client.post(f"/logistique/{lr.token}/", {})
    assert response.status_code == 403


# ── Envoi de lien logistique ──────────────────────────────────────────────────

@pytest.mark.django_db
def test_send_link_sends_email_to_respondent(client, mailoutbox):
    """L'organisateur peut envoyer le lien logistique à un intervenant."""
    membership = MembershipFactory(role="organizer")
    lf = LogisticsFormFactory(event=membership.event, is_open=True)
    lr = LogisticsResponseFactory(form=lf)
    client.force_login(membership.user)
    response = client.post(
        f"/evenements/{membership.event.slug}/logistique/{lf.pk}/reponses/{lr.pk}/envoyer-lien/"
    )
    assert response.status_code == 302
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == [lr.respondent_email]


@pytest.mark.django_db
def test_send_all_links_sends_to_incomplete_only(client, mailoutbox):
    """Envoyer tous les liens ne cible que les réponses incomplètes."""
    membership = MembershipFactory(role="organizer")
    lf = LogisticsFormFactory(event=membership.event, is_open=True)
    LogisticsResponseFactory(form=lf, is_complete=False)
    LogisticsResponseFactory(form=lf, is_complete=False)
    LogisticsResponseFactory(form=lf, is_complete=True)
    client.force_login(membership.user)
    client.post(
        f"/evenements/{membership.event.slug}/logistique/{lf.pk}/reponses/envoyer-tous/"
    )
    assert len(mailoutbox) == 2


# ── Export CSV ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_export_csv_returns_csv_content_type(client):
    membership = MembershipFactory(role="organizer")
    lf = LogisticsFormFactory(event=membership.event)
    client.force_login(membership.user)
    response = client.get(
        f"/evenements/{membership.event.slug}/logistique/{lf.pk}/reponses/export.csv"
    )
    assert response.status_code == 200
    assert "text/csv" in response["Content-Type"]


@pytest.mark.django_db
def test_export_csv_contains_respondent_name(client):
    membership = MembershipFactory(role="organizer")
    lf = LogisticsFormFactory(event=membership.event)
    LogisticsResponseFactory(form=lf, respondent_name="Jeanne Durand")
    client.force_login(membership.user)
    response = client.get(
        f"/evenements/{membership.event.slug}/logistique/{lf.pk}/reponses/export.csv"
    )
    assert "Jeanne Durand" in response.content.decode()
