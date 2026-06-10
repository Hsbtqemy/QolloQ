from django.urls import path

from . import views_staff

app_name = "staff"

urlpatterns = [
    path("staff/", views_staff.StaffDashboardView.as_view(), name="dashboard"),
    path("staff/utilisateurs/", views_staff.StaffUserListView.as_view(), name="users"),
    path("staff/utilisateurs/creer/", views_staff.StaffUserCreateView.as_view(), name="user_create"),
    path("staff/utilisateurs/<int:pk>/modifier/", views_staff.StaffUserEditView.as_view(), name="user_edit"),
    path("staff/email-templates/", views_staff.StaffEmailTemplateListView.as_view(), name="email_templates"),
    path("staff/email-templates/<str:key>/", views_staff.StaffEmailTemplateEditView.as_view(), name="email_template_edit"),
]
