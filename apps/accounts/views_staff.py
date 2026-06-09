from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.core.mixins import SuperuserRequiredMixin
from apps.events.models import Event
from apps.submissions.models import Proposal

from .forms_staff import StaffUserCreateForm, StaffUserEditForm

User = get_user_model()


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
