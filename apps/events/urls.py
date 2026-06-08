from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("evenements/nouveau/", views.EventCreateView.as_view(), name="create"),
    path("evenements/<slug:event_slug>/", views.EventDetailView.as_view(), name="detail"),
    path("evenements/<slug:event_slug>/parametres/", views.EventSettingsView.as_view(), name="settings"),
]
