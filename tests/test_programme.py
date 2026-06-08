import pytest

from .factories import CommunicationFactory, EventFactory, MembershipFactory, SessionFactory

try:
    import weasyprint  # noqa: F401
    HAS_WEASYPRINT = True
except OSError:
    HAS_WEASYPRINT = False


@pytest.mark.django_db
def test_programme_view_200(client):
    membership = MembershipFactory(role="organizer")
    client.force_login(membership.user)
    response = client.get(f"/evenements/{membership.event.slug}/programme/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_programme_view_requires_login(client):
    event = EventFactory()
    response = client.get(f"/evenements/{event.slug}/programme/")
    assert response.status_code == 302


@pytest.mark.skipif(not HAS_WEASYPRINT, reason="Pango non disponible (brew install pango)")
@pytest.mark.django_db
def test_programme_pdf_returns_pdf(client):
    membership = MembershipFactory(role="organizer")
    SessionFactory(event=membership.event)
    client.force_login(membership.user)
    response = client.get(f"/evenements/{membership.event.slug}/programme/pdf/")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert len(response.content) > 0


@pytest.mark.django_db
def test_programme_pdf_requires_login(client):
    event = EventFactory()
    response = client.get(f"/evenements/{event.slug}/programme/pdf/")
    assert response.status_code == 302


@pytest.mark.django_db
def test_session_create(client):
    membership = MembershipFactory(role="organizer")
    event = membership.event
    client.force_login(membership.user)
    response = client.post(f"/evenements/{event.slug}/programme/sessions/", {
        "date": str(event.start_date),
        "start_time": "09:00",
        "end_time": "10:30",
        "title": "Ouverture",
    })
    assert response.status_code == 302
    assert event.sessions.filter(title="Ouverture").exists()


@pytest.mark.django_db
def test_session_reorder_invalid_json(client):
    membership = MembershipFactory(role="organizer")
    client.force_login(membership.user)
    response = client.post(
        f"/evenements/{membership.event.slug}/programme/sessions/reorder/",
        data="not json",
        content_type="application/json",
    )
    assert response.status_code == 400
