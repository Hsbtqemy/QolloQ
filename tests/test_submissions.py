import uuid

import pytest

from apps.submissions.models import Proposal

from .factories import EventFactory, MembershipFactory, ProposalFactory, UserFactory


# ── Flux public ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_submit_get_closed(client):
    event = EventFactory(submissions_open=False)
    response = client.get(f"/soumettre/{event.slug}/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_submit_get_open(client):
    event = EventFactory(submissions_open=True)
    response = client.get(f"/soumettre/{event.slug}/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_submit_creates_proposal(client, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    event = EventFactory(submissions_open=True)
    response = client.post(f"/soumettre/{event.slug}/", {
        "title": "Une communication",
        "abstract": "Un résumé.",
        "submitter_email": "auteur@example.com",
        # management form du AuthorFormSet (préfixe "authors" = related_name du FK)
        "authors-TOTAL_FORMS": "1",
        "authors-INITIAL_FORMS": "0",
        "authors-MIN_NUM_FORMS": "1",
        "authors-MAX_NUM_FORMS": "1000",
        "authors-0-first_name": "Marie",
        "authors-0-last_name": "Dupont",
        "authors-0-institution": "CNRS",
        "authors-0-email": "auteur@example.com",
    })
    assert response.status_code == 302
    assert Proposal.objects.filter(event=event, submitter_email="auteur@example.com").exists()


@pytest.mark.django_db
def test_token_access_200(client):
    proposal = ProposalFactory()
    response = client.get(f"/ma-soumission/{proposal.token}/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_token_access_404_unknown(client):
    response = client.get(f"/ma-soumission/{uuid.uuid4()}/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_resend_token_get(client):
    event = EventFactory()
    response = client.get(f"/soumettre/{event.slug}/lien/")
    assert response.status_code == 200


# ── Vues organisateur ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_proposal_list_requires_login(client):
    event = EventFactory()
    response = client.get(f"/evenements/{event.slug}/soumissions/")
    assert response.status_code == 302


@pytest.mark.django_db
def test_proposal_list_requires_membership(client):
    user = UserFactory()
    event = EventFactory()
    client.force_login(user)
    response = client.get(f"/evenements/{event.slug}/soumissions/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_proposal_list_organizer_200(client):
    membership = MembershipFactory(role="organizer")
    client.force_login(membership.user)
    response = client.get(f"/evenements/{membership.event.slug}/soumissions/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_proposal_list_committee_200(client):
    membership = MembershipFactory(role="committee")
    client.force_login(membership.user)
    response = client.get(f"/evenements/{membership.event.slug}/soumissions/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_proposal_list_speaker_403(client):
    membership = MembershipFactory(role="speaker")
    client.force_login(membership.user)
    response = client.get(f"/evenements/{membership.event.slug}/soumissions/")
    assert response.status_code == 403
