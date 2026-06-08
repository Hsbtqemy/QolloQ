from django.urls import path

from . import views

app_name = "site_public"

urlpatterns = [
    path(
        "evenements/<slug:event_slug>/site/publier/",
        views.SitePublishView.as_view(),
        name="publish",
    ),
]
