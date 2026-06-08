from django.urls import path

from . import views

app_name = "logistics"

urlpatterns = [
    # Index — liste des formulaires de l'événement
    path(
        "evenements/<slug:event_slug>/logistique/",
        views.LogisticsIndexView.as_view(),
        name="index",
    ),
    # CRUD d'un formulaire
    path(
        "evenements/<slug:event_slug>/logistique/<int:form_id>/",
        views.LogisticsSettingsView.as_view(),
        name="settings",
    ),
    path(
        "evenements/<slug:event_slug>/logistique/<int:form_id>/supprimer/",
        views.LogisticsFormDeleteView.as_view(),
        name="form_delete",
    ),
    # Champs d'un formulaire
    path(
        "evenements/<slug:event_slug>/logistique/<int:form_id>/champs/ajouter/",
        views.FieldCreateView.as_view(),
        name="field_create",
    ),
    path(
        "evenements/<slug:event_slug>/logistique/<int:form_id>/champs/<int:field_id>/modifier/",
        views.FieldEditView.as_view(),
        name="field_edit",
    ),
    path(
        "evenements/<slug:event_slug>/logistique/<int:form_id>/champs/<int:field_id>/supprimer/",
        views.FieldDeleteView.as_view(),
        name="field_delete",
    ),
    path(
        "evenements/<slug:event_slug>/logistique/<int:form_id>/champs/reordonner/",
        views.FieldReorderView.as_view(),
        name="field_reorder",
    ),
    # Réponses d'un formulaire
    path(
        "evenements/<slug:event_slug>/logistique/<int:form_id>/reponses/",
        views.ResponseListView.as_view(),
        name="response_list",
    ),
    path(
        "evenements/<slug:event_slug>/logistique/<int:form_id>/reponses/ajouter/",
        views.ResponseCreateView.as_view(),
        name="response_create",
    ),
    path(
        "evenements/<slug:event_slug>/logistique/<int:form_id>/reponses/<int:response_id>/",
        views.ResponseDetailView.as_view(),
        name="response_detail",
    ),
    path(
        "evenements/<slug:event_slug>/logistique/<int:form_id>/reponses/<int:response_id>/supprimer/",
        views.ResponseDeleteView.as_view(),
        name="response_delete",
    ),
    path(
        "evenements/<slug:event_slug>/logistique/<int:form_id>/reponses/<int:response_id>/envoyer-lien/",
        views.SendLinkView.as_view(),
        name="send_link",
    ),
    path(
        "evenements/<slug:event_slug>/logistique/<int:form_id>/reponses/envoyer-tous/",
        views.SendAllLinksView.as_view(),
        name="send_all_links",
    ),
    path(
        "evenements/<slug:event_slug>/logistique/<int:form_id>/reponses/export.csv",
        views.ResponseExportView.as_view(),
        name="export_csv",
    ),
    # Accès public via token
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
