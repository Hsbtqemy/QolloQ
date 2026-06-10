import json
import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.submissions.models import Evaluation, Proposal

from .factories import EventFactory, MembershipFactory, ProposalFactory, UserFactory


# ── Helpers ───────────────────────────────────────────────────────────────────

def _post_data(**overrides):
    data = {
        "title": "Une communication",
        "abstract": "Un résumé.",
        "bio": "Courte bio.",
        "submitter_email": "auteur@example.com",
        "authors-TOTAL_FORMS": "1",
        "authors-INITIAL_FORMS": "0",
        "authors-MIN_NUM_FORMS": "1",
        "authors-MAX_NUM_FORMS": "1000",
        "authors-0-first_name": "Marie",
        "authors-0-last_name": "Dupont",
        "authors-0-institution": "CNRS",
        "authors-0-email": "auteur@example.com",
    }
    data.update(overrides)
    return data


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
def test_submit_creates_proposal(client, mailoutbox):
    event = EventFactory(submissions_open=True)
    response = client.post(f"/soumettre/{event.slug}/", _post_data())
    assert response.status_code == 302
    assert Proposal.objects.filter(event=event, submitter_email="auteur@example.com").exists()


@pytest.mark.django_db
def test_submit_sends_confirmation_email(client, mailoutbox):
    """Soumission → au moins un email de confirmation vers le soumettant."""
    event = EventFactory(submissions_open=True)
    client.post(f"/soumettre/{event.slug}/", _post_data())
    recipients = [m.to[0] for m in mailoutbox]
    assert "auteur@example.com" in recipients


@pytest.mark.django_db
def test_submit_notifies_organizer(client, mailoutbox):
    """Soumission → l'organisateur reçoit une notification en plus de la confirmation."""
    membership = MembershipFactory(role="organizer")
    event = membership.event
    event.submissions_open = True
    event.save()
    client.post(f"/soumettre/{event.slug}/", _post_data())
    recipients = [m.to[0] for m in mailoutbox]
    assert "auteur@example.com" in recipients
    assert membership.user.email in recipients


@pytest.mark.django_db
def test_submit_notifies_all_organizers(client, mailoutbox):
    """Avec deux organisateurs, chacun reçoit une notification."""
    event = EventFactory(submissions_open=True)
    org1 = MembershipFactory(event=event, role="organizer")
    org2 = MembershipFactory(event=event, role="organizer")
    client.post(f"/soumettre/{event.slug}/", _post_data())
    recipients = [m.to[0] for m in mailoutbox]
    assert org1.user.email in recipients
    assert org2.user.email in recipients


@pytest.mark.django_db
def test_submit_no_notification_without_organizer(client, mailoutbox):
    """Sans organisateur, seul l'email de confirmation part (pas d'erreur)."""
    event = EventFactory(submissions_open=True)
    client.post(f"/soumettre/{event.slug}/", _post_data())
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == ["auteur@example.com"]


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


@pytest.mark.django_db
def test_resend_token_post_sends_email(client, mailoutbox):
    """Le renvoi de lien envoie un email si l'adresse correspond à une proposition."""
    proposal = ProposalFactory()
    event = proposal.event
    client.post(f"/soumettre/{event.slug}/lien/", {"email": proposal.submitter_email})
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == [proposal.submitter_email]


@pytest.mark.django_db
def test_resend_token_post_unknown_email(client, mailoutbox):
    """Le renvoi de lien ne crash pas et n'envoie rien si l'email est inconnu."""
    event = EventFactory()
    response = client.post(f"/soumettre/{event.slug}/lien/", {"email": "inconnu@example.com"})
    assert response.status_code == 200
    assert len(mailoutbox) == 0


# ── Accès évaluateur tokenisé ─────────────────────────────────────────────────

@pytest.mark.django_db
def test_evaluator_access_200(client):
    membership = MembershipFactory(role="committee", eval_token=uuid.uuid4())
    response = client.get(f"/evaluer/{membership.eval_token}/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_evaluator_access_404_unknown(client):
    response = client.get(f"/evaluer/{uuid.uuid4()}/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_evaluator_eval_post_creates_evaluation(client):
    """Un évaluateur peut déposer un avis via son token."""
    membership = MembershipFactory(role="committee", eval_token=uuid.uuid4())
    proposal = ProposalFactory(event=membership.event)
    response = client.post(
        f"/evaluer/{membership.eval_token}/{proposal.pk}/",
        {"verdict": Evaluation.Verdict.FOR, "comment": "Très bon."},
    )
    assert response.status_code == 302
    assert Evaluation.objects.filter(proposal=proposal, evaluator=membership).exists()


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


@pytest.mark.django_db
def test_proposal_status_update(client):
    """L'organisateur peut changer le statut via POST JSON."""
    membership = MembershipFactory(role="organizer")
    proposal = ProposalFactory(event=membership.event, status="submitted")
    client.force_login(membership.user)
    response = client.post(
        f"/evenements/{membership.event.slug}/soumissions/{proposal.pk}/statut/",
        data=json.dumps({"status": "accepted"}),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    proposal.refresh_from_db()
    assert proposal.status == "accepted"


# ── Deadline ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_submit_deadline_past_get_404(client):
    """GET du formulaire public retourne 404 si la deadline est dépassée."""
    event = EventFactory(
        submissions_open=True,
        submission_deadline=timezone.now() - timedelta(hours=1),
    )
    response = client.get(f"/soumettre/{event.slug}/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_submit_deadline_past_post_404(client):
    """POST au formulaire public retourne 404 si la deadline est dépassée."""
    event = EventFactory(
        submissions_open=True,
        submission_deadline=timezone.now() - timedelta(hours=1),
    )
    response = client.post(f"/soumettre/{event.slug}/", _post_data())
    assert response.status_code == 404


# ── Token : modification et retrait ──────────────────────────────────────────

@pytest.mark.django_db
def test_token_edit_updates_title(client):
    """Le soumettant peut modifier le titre de sa proposition via son token."""
    proposal = ProposalFactory(status="submitted")
    response = client.post(
        f"/ma-soumission/{proposal.token}/",
        _post_data(title="Nouveau titre"),
    )
    assert response.status_code == 302
    proposal.refresh_from_db()
    assert proposal.title == "Nouveau titre"


@pytest.mark.django_db
def test_token_edit_rejected_if_not_submitted(client):
    """Une proposition non soumise (acceptée) n'est plus modifiable."""
    proposal = ProposalFactory(status="accepted")
    response = client.post(
        f"/ma-soumission/{proposal.token}/",
        _post_data(title="Tentative"),
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_token_withdraw_deletes_proposal(client):
    """Le soumettant peut retirer sa proposition via son token (hard delete)."""
    proposal = ProposalFactory(status="submitted")
    token = proposal.token
    response = client.post(
        f"/ma-soumission/{proposal.token}/",
        {"action": "withdraw"},
    )
    assert response.status_code == 200
    assert not Proposal.objects.filter(token=token).exists()


# ── Détail proposition ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_proposal_detail_organizer_200(client):
    membership = MembershipFactory(role="organizer")
    proposal = ProposalFactory(event=membership.event)
    client.force_login(membership.user)
    response = client.get(
        f"/evenements/{membership.event.slug}/soumissions/{proposal.pk}/"
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_proposal_detail_committee_200(client):
    membership = MembershipFactory(role="committee")
    proposal = ProposalFactory(event=membership.event)
    client.force_login(membership.user)
    response = client.get(
        f"/evenements/{membership.event.slug}/soumissions/{proposal.pk}/"
    )
    assert response.status_code == 200


# ── Évaluation (connecté) ─────────────────────────────────────────────────────

@pytest.mark.django_db
def test_evaluation_submit_by_logged_in_committee(client):
    """Un membre comité connecté peut soumettre un avis."""
    membership = MembershipFactory(role="committee")
    proposal = ProposalFactory(event=membership.event)
    client.force_login(membership.user)
    response = client.post(
        f"/evenements/{membership.event.slug}/soumissions/{proposal.pk}/evaluer/",
        {"verdict": Evaluation.Verdict.FOR, "comment": "Proposition solide."},
    )
    assert response.status_code == 302
    assert Evaluation.objects.filter(proposal=proposal, evaluator=membership).exists()


@pytest.mark.django_db
def test_evaluation_update_replaces_existing(client):
    """Un second avis du même évaluateur remplace le premier."""
    membership = MembershipFactory(role="committee")
    proposal = ProposalFactory(event=membership.event)
    client.force_login(membership.user)
    for verdict in (Evaluation.Verdict.HESITANT, Evaluation.Verdict.AGAINST):
        client.post(
            f"/evenements/{membership.event.slug}/soumissions/{proposal.pk}/evaluer/",
            {"verdict": verdict, "comment": ""},
        )
    assert Evaluation.objects.filter(proposal=proposal, evaluator=membership).count() == 1
    assert Evaluation.objects.get(proposal=proposal, evaluator=membership).verdict == Evaluation.Verdict.AGAINST


# ── Création / édition directe par l'organisateur ────────────────────────────

@pytest.mark.django_db
def test_organizer_creates_proposal_directly(client):
    """L'organisateur peut saisir une proposition sans passer par le flux public."""
    membership = MembershipFactory(role="organizer")
    client.force_login(membership.user)
    response = client.post(
        f"/evenements/{membership.event.slug}/soumissions/nouveau/",
        _post_data(status="submitted"),
    )
    assert response.status_code == 302
    assert Proposal.objects.filter(
        event=membership.event, submitter_email="auteur@example.com"
    ).exists()


@pytest.mark.django_db
def test_organizer_edits_proposal(client):
    """L'organisateur peut modifier le titre d'une proposition existante."""
    membership = MembershipFactory(role="organizer")
    proposal = ProposalFactory(event=membership.event)
    client.force_login(membership.user)
    response = client.post(
        f"/evenements/{membership.event.slug}/soumissions/{proposal.pk}/modifier/",
        _post_data(title="Titre corrigé", status="submitted"),
    )
    assert response.status_code == 302
    proposal.refresh_from_db()
    assert proposal.title == "Titre corrigé"
