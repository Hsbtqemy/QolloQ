from django.urls import path

from . import views

app_name = "logistics"

urlpatterns = [
    # Organizer — settings & fields
    path(
        "evenements/<slug:event_slug>/logistique/",
        views.LogisticsSettingsView.as_view(),
        name="settings",
    ),
    path(
        "evenements/<slug:event_slug>/logistique/champs/ajouter/",
        views.FieldCreateView.as_view(),
        name="field_create",
    ),
    path(
        "evenements/<slug:event_slug>/logistique/champs/<int:field_id>/modifier/",
        views.FieldEditView.as_view(),
        name="field_edit",
    ),
    path(
        "evenements/<slug:event_slug>/logistique/champs/<int:field_id>/supprimer/",
        views.FieldDeleteView.as_view(),
        name="field_delete",
    ),
    path(
        "evenements/<slug:event_slug>/logistique/champs/reordonner/",
        views.FieldReorderView.as_view(),
        name="field_reorder",
    ),
    # Organizer / committee — responses
    path(
        "evenements/<slug:event_slug>/logistique/reponses/",
        views.ResponseListView.as_view(),
        name="response_list",
    ),
    path(
        "evenements/<slug:event_slug>/logistique/reponses/ajouter/",
        views.ResponseCreateView.as_view(),
        name="response_create",
    ),
    path(
        "evenements/<slug:event_slug>/logistique/reponses/<int:response_id>/",
        views.ResponseDetailView.as_view(),
        name="response_detail",
    ),
    path(
        "evenements/<slug:event_slug>/logistique/reponses/<int:response_id>/supprimer/",
        views.ResponseDeleteView.as_view(),
        name="response_delete",
    ),
    path(
        "evenements/<slug:event_slug>/logistique/reponses/<int:response_id>/envoyer-lien/",
        views.SendLinkView.as_view(),
        name="send_link",
    ),
    path(
        "evenements/<slug:event_slug>/logistique/reponses/envoyer-tous/",
        views.SendAllLinksView.as_view(),
        name="send_all_links",
    ),
    # Public — token access
    path(
        "logistique/<uuid:token>/",
        views.PublicRespondView.as_view(),
        name="respond",
    ),
    path(
        "logistique/<uuid:token>/merci/",
        views.PublicRespondDoneView.as_view(),
        name="respond_done",
    ),
]
