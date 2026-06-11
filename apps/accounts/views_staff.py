from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm
from django.db import models as db_models
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.core.mixins import SuperuserRequiredMixin
from apps.emails.models import EmailTemplate
from apps.events.models import Event
from apps.submissions.models import Proposal

from .forms_staff import StaffUserCreateForm, StaffUserEditForm

User = get_user_model()


class EmailTemplateForm(forms.ModelForm):
    class Meta:
        model = EmailTemplate
        fields = ["subject_fr", "subject_en", "body_fr", "body_en"]
        widgets = {
            "subject_fr": forms.TextInput(attrs={"class": "input"}),
            "subject_en": forms.TextInput(attrs={"class": "input"}),
            "body_fr": forms.Textarea(attrs={"class": "input", "rows": 14, "style": "font-family:monospace;font-size:.9em"}),
            "body_en": forms.Textarea(attrs={"class": "input", "rows": 14, "style": "font-family:monospace;font-size:.9em"}),
        }


class StaffDashboardView(SuperuserRequiredMixin, View):
    def get(self, request):
        events = Event.objects.annotate(
            member_count=Count("memberships", distinct=True),
            submission_count=Count("proposals", distinct=True),
        ).order_by("-created_at")
        return render(request, "staff/dashboard.html", {
            "events": events,
            "total_users": User.objects.filter(is_active=True).count(),
            "total_events": events.count(),
            "total_submissions": Proposal.objects.count(),
        })


class StaffUserListView(SuperuserRequiredMixin, View):
    def get(self, request):
        users = User.objects.annotate(
            event_count=Count("memberships", distinct=True),
        ).order_by("last_name", "first_name", "email")
        return render(request, "staff/users.html", {"users": users})


class StaffUserCreateView(SuperuserRequiredMixin, View):
    def get(self, request):
        return render(request, "staff/user_form.html", {"form": StaffUserCreateForm()})

    def post(self, request):
        form = StaffUserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Compte {user.email} créé.")
            return redirect("staff:users")
        return render(request, "staff/user_form.html", {"form": form})


class StaffUserEditView(SuperuserRequiredMixin, View):
    def get(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        return render(request, "staff/user_form.html", {
            "form": StaffUserEditForm(instance=target),
            "target_user": target,
            "password_form": SetPasswordForm(target),
        })

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        if request.POST.get("action") == "set_password":
            form = SetPasswordForm(target, request.POST)
            if form.is_valid():
                form.save()
                target.must_change_password = True
                target.save(update_fields=["must_change_password"])
                messages.success(request, "Mot de passe réinitialisé.")
            else:
                messages.error(request, "Erreur dans le formulaire.")
            return redirect("staff:user_edit", pk=pk)
        form = StaffUserEditForm(request.POST, instance=target)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil mis à jour.")
            return redirect("staff:users")
        return render(request, "staff/user_form.html", {
            "form": form,
            "target_user": target,
            "password_form": SetPasswordForm(target),
        })


class StaffUserDeleteView(SuperuserRequiredMixin, View):
    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        if target == request.user:
            messages.error(request, "Vous ne pouvez pas supprimer votre propre compte.")
            return redirect("staff:user_edit", pk=pk)
        try:
            email = target.email
            target.delete()
            messages.success(request, f"Compte {email} supprimé.")
        except db_models.ProtectedError:
            messages.error(request, "Ce compte ne peut pas être supprimé car il est lié à des événements.")
        return redirect("staff:users")


class StaffEmailTemplateListView(SuperuserRequiredMixin, View):
    def get(self, request):
        templates = EmailTemplate.objects.all()
        return render(request, "staff/email_templates.html", {"templates": templates})


class StaffEmailTemplateEditView(SuperuserRequiredMixin, View):
    def get(self, request, key):
        tmpl = get_object_or_404(EmailTemplate, key=key)
        return render(request, "staff/email_template_edit.html", {
            "tmpl": tmpl,
            "form": EmailTemplateForm(instance=tmpl),
            "variables": tmpl.variables_help(),
        })

    def post(self, request, key):
        tmpl = get_object_or_404(EmailTemplate, key=key)
        form = EmailTemplateForm(request.POST, instance=tmpl)
        if form.is_valid():
            form.save()
            messages.success(request, "Template mis à jour.")
            return redirect("staff:email_templates")
        return render(request, "staff/email_template_edit.html", {
            "tmpl": tmpl,
            "form": form,
            "variables": tmpl.variables_help(),
        })
