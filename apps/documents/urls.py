from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    path(
        "evenements/<slug:event_slug>/documents/",
        views.DocumentCreateView.as_view(),
        name="create",
    ),
    path(
        "evenements/<slug:event_slug>/documents/<int:doc_id>/supprimer/",
        views.DocumentDeleteView.as_view(),
        name="delete",
    ),
    path(
        "evenements/<slug:event_slug>/documents/<int:doc_id>/telecharger/",
        views.DocumentDownloadView.as_view(),
        name="download",
    ),
]
