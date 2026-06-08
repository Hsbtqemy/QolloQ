from django.urls import path

from . import views

app_name = "programme"

urlpatterns = [
    path(
        "evenements/<slug:event_slug>/programme/",
        views.ProgrammeView.as_view(),
        name="programme",
    ),
    path(
        "evenements/<slug:event_slug>/programme/calendrier/",
        views.CalendarView.as_view(),
        name="calendar",
    ),
    path(
        "evenements/<slug:event_slug>/programme/pdf/",
        views.ProgrammePdfView.as_view(),
        name="pdf",
    ),

    # Sessions
    path(
        "evenements/<slug:event_slug>/programme/sessions/",
        views.SessionCreateView.as_view(),
        name="session_create",
    ),
    path(
        "evenements/<slug:event_slug>/programme/sessions/reorder/",
        views.SessionReorderView.as_view(),
        name="session_reorder",
    ),
    path(
        "evenements/<slug:event_slug>/programme/sessions/<int:session_id>/",
        views.SessionUpdateView.as_view(),
        name="session_update",
    ),
    path(
        "evenements/<slug:event_slug>/programme/sessions/<int:session_id>/supprimer/",
        views.SessionDeleteView.as_view(),
        name="session_delete",
    ),

    # Communications
    path(
        "evenements/<slug:event_slug>/programme/sessions/<int:session_id>/communications/",
        views.CommunicationCreateView.as_view(),
        name="comm_create",
    ),
    path(
        "evenements/<slug:event_slug>/programme/communications/reorder/",
        views.CommunicationReorderView.as_view(),
        name="comm_reorder",
    ),
    path(
        "evenements/<slug:event_slug>/programme/communications/<int:comm_id>/",
        views.CommunicationUpdateView.as_view(),
        name="comm_update",
    ),
    path(
        "evenements/<slug:event_slug>/programme/communications/<int:comm_id>/supprimer/",
        views.CommunicationDeleteView.as_view(),
        name="comm_delete",
    ),

    # Événements annexes
    path(
        "evenements/<slug:event_slug>/programme/annexes/",
        views.AnnexEventCreateView.as_view(),
        name="annex_create",
    ),
    path(
        "evenements/<slug:event_slug>/programme/annexes/<int:annex_id>/",
        views.AnnexEventUpdateView.as_view(),
        name="annex_update",
    ),
    path(
        "evenements/<slug:event_slug>/programme/annexes/<int:annex_id>/supprimer/",
        views.AnnexEventDeleteView.as_view(),
        name="annex_delete",
    ),
]
