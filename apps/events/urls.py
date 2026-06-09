from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("evenements/nouveau/", views.EventCreateView.as_view(), name="create"),
    path("evenements/<slug:event_slug>/", views.EventDetailView.as_view(), name="detail"),
    path("evenements/<slug:event_slug>/parametres/", views.EventSettingsView.as_view(), name="settings"),
    path("evenements/<slug:event_slug>/membres/", views.MemberListView.as_view(), name="members"),
    path("evenements/<slug:event_slug>/membres/ajouter/", views.MemberAddView.as_view(), name="member_add"),
    path("evenements/<slug:event_slug>/membres/<int:membership_id>/role/", views.MemberUpdateView.as_view(), name="member_update"),
    path("evenements/<slug:event_slug>/membres/<int:membership_id>/retirer/", views.MemberRemoveView.as_view(), name="member_remove"),
    path("evenements/<slug:event_slug>/contenu/", views.EventPublicSettingsView.as_view(), name="public_settings"),
    path("evenements/<slug:event_slug>/contenu/importer/", views.EventImportCallView.as_view(), name="import_call"),
    path("evenements/<slug:event_slug>/contenu/versions/creer/", views.CallVersionCreateView.as_view(), name="call_version_create"),
    path("evenements/<slug:event_slug>/contenu/versions/<int:pk>/modifier/", views.CallVersionUpdateView.as_view(), name="call_version_update"),
    path("evenements/<slug:event_slug>/contenu/versions/<int:pk>/supprimer/", views.CallVersionDeleteView.as_view(), name="call_version_delete"),
    path("evenements/<slug:event_slug>/dates/ajouter/", views.KeyDateCreateView.as_view(), name="keydate_create"),
    path("evenements/<slug:event_slug>/dates/<int:pk>/supprimer/", views.KeyDateDeleteView.as_view(), name="keydate_delete"),
    path("evenements/<slug:event_slug>/taches/ajouter/", views.TaskCreateView.as_view(), name="task_create"),
    path("evenements/<slug:event_slug>/taches/<int:pk>/toggle/", views.TaskToggleView.as_view(), name="task_toggle"),
    path("evenements/<slug:event_slug>/taches/<int:pk>/supprimer/", views.TaskDeleteView.as_view(), name="task_delete"),
]
