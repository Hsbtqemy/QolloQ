from django.urls import path

from . import views

app_name = "site_public"

urlpatterns = [
    path(
        "evenements/<slug:event_slug>/site/publier/",
        views.SitePublishView.as_view(),
        name="publish",
    ),
    path(
        "appel/<slug:event_slug>/",
        views.EventPublicView.as_view(),
        name="page",
    ),
    path(
        "appel/<slug:event_slug>/pdf/",
        views.EventCallPDFView.as_view(),
        name="call_pdf",
    ),
]
