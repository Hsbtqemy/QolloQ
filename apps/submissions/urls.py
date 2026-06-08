from django.urls import path

from . import views

app_name = "submissions"

urlpatterns = [
    # Flux public (sans compte)
    path(
        "soumettre/<slug:event_slug>/",
        views.PublicSubmitView.as_view(),
        name="public_submit",
    ),
    path(
        "soumettre/<slug:event_slug>/lien/",
        views.ResendTokenView.as_view(),
        name="resend_token",
    ),
    path(
        "ma-soumission/<uuid:token>/",
        views.TokenAccessView.as_view(),
        name="token_access",
    ),
    path(
        "ma-soumission/<uuid:token>/confirmation/",
        views.SubmissionSubmittedView.as_view(),
        name="submitted",
    ),

    # Vues organisateur / comité
    path(
        "evenements/<slug:event_slug>/soumissions/",
        views.ProposalListView.as_view(),
        name="list",
    ),
    path(
        "evenements/<slug:event_slug>/soumissions/nouveau/",
        views.ProposalCreateView.as_view(),
        name="create",
    ),
    path(
        "evenements/<slug:event_slug>/soumissions/<int:proposal_id>/",
        views.ProposalDetailView.as_view(),
        name="detail",
    ),
    path(
        "evenements/<slug:event_slug>/soumissions/<int:proposal_id>/statut/",
        views.ProposalStatusView.as_view(),
        name="status",
    ),
    path(
        "evenements/<slug:event_slug>/soumissions/<int:proposal_id>/modifier/",
        views.ProposalEditView.as_view(),
        name="edit",
    ),
    path(
        "evenements/<slug:event_slug>/soumissions/<int:proposal_id>/evaluer/",
        views.EvaluationSubmitView.as_view(),
        name="evaluate",
    ),
]
