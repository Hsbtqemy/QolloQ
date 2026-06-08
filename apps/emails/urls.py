from django.urls import path

from . import views

app_name = "emails"

urlpatterns = [
    path(
        "evenements/<slug:event_slug>/emails/",
        views.CampaignListView.as_view(),
        name="campaign_list",
    ),
    path(
        "evenements/<slug:event_slug>/emails/nouveau/",
        views.CampaignCreateView.as_view(),
        name="campaign_create",
    ),
    path(
        "evenements/<slug:event_slug>/emails/<int:pk>/",
        views.CampaignDetailView.as_view(),
        name="campaign_detail",
    ),
    path(
        "evenements/<slug:event_slug>/emails/<int:pk>/modifier/",
        views.CampaignEditView.as_view(),
        name="campaign_edit",
    ),
    path(
        "evenements/<slug:event_slug>/emails/<int:pk>/supprimer/",
        views.CampaignDeleteView.as_view(),
        name="campaign_delete",
    ),
    path(
        "evenements/<slug:event_slug>/emails/<int:pk>/envoyer/",
        views.CampaignSendView.as_view(),
        name="campaign_send",
    ),
]
