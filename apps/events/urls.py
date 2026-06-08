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
]
