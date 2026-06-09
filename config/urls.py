from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("", include("apps.events.urls")),
    path("", include("apps.submissions.urls")),
    path("", include("apps.programme.urls")),
    path("", include("apps.documents.urls")),
    path("", include("apps.logistics.urls")),
    path("", include("apps.emails.urls")),
    path("", include("apps.site_public.urls")),
    path("", include("apps.accounts.urls")),
]
