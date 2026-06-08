import zipfile

import pytest

from .factories import (
    AuthorFactory,
    EventFactory,
    MembershipFactory,
    ProposalFactory,
    SessionFactory,
    CommunicationFactory,
)


@pytest.mark.django_db
def test_build_site_zip_contains_expected_files(rf):
    from apps.site_public.builder import build_site_zip

    event = EventFactory(submissions_open=False)
    request = rf.get("/")

    buf = build_site_zip(event, request)

    with zipfile.ZipFile(buf) as zf:
        names = zf.namelist()

    assert "index.html" in names
    assert "programme.html" in names
    assert "intervenants.html" in names
    assert "css/style.css" in names


@pytest.mark.django_db
def test_build_site_zip_includes_speakers(rf):
    from apps.site_public.builder import build_site_zip

    event = EventFactory(submissions_open=False)
    proposal = ProposalFactory(event=event, status="accepted")
    AuthorFactory(proposal=proposal, first_name="Jean", last_name="Martin")
    request = rf.get("/")

    buf = build_site_zip(event, request)

    with zipfile.ZipFile(buf) as zf:
        speakers_html = zf.read("intervenants.html").decode()

    assert "Jean Martin" in speakers_html
    assert proposal.title in speakers_html


@pytest.mark.django_db
def test_build_site_zip_programme_content(rf):
    from apps.site_public.builder import build_site_zip

    event = EventFactory(submissions_open=False)
    session = SessionFactory(event=event, title="Session inaugurale")
    CommunicationFactory(session=session, title="Ma communication", speaker_name="A. Chercheur")
    request = rf.get("/")

    buf = build_site_zip(event, request)

    with zipfile.ZipFile(buf) as zf:
        programme_html = zf.read("programme.html").decode()

    assert "Session inaugurale" in programme_html
    assert "Ma communication" in programme_html
    assert "A. Chercheur" in programme_html


@pytest.mark.django_db
def test_publish_view_returns_zip(client):
    membership = MembershipFactory(role="organizer")
    client.force_login(membership.user)
    response = client.post(
        f"/evenements/{membership.event.slug}/site/publier/"
    )
    assert response.status_code == 200
    assert response["Content-Type"] == "application/zip"


@pytest.mark.django_db
def test_publish_view_requires_organizer(client):
    membership = MembershipFactory(role="committee")
    client.force_login(membership.user)
    response = client.post(
        f"/evenements/{membership.event.slug}/site/publier/"
    )
    assert response.status_code == 403
