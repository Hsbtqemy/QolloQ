from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from apps.events.models import Event, Membership


class EventMemberRequiredMixin(LoginRequiredMixin):
    """Vérifie que l'utilisateur est membre de l'événement (tout rôle).

    Résout self.event et self.membership avant d'appeler get/post.
    Les sous-classes peuvent surcharger check_membership_permissions()
    pour ajouter des contraintes sur le rôle.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        event_slug = kwargs.get("event_slug")
        self.event = get_object_or_404(Event, slug=event_slug)
        try:
            self.membership = Membership.objects.get(user=request.user, event=self.event)
        except Membership.DoesNotExist:
            raise PermissionDenied
        self.check_membership_permissions()
        return super().dispatch(request, *args, **kwargs)

    def check_membership_permissions(self):
        pass


class CommitteeRequiredMixin(EventMemberRequiredMixin):
    """Organisateurs et membres du comité scientifique (exclut les intervenants)."""

    def check_membership_permissions(self):
        if not self.membership.is_committee:
            raise PermissionDenied


class OrganizerRequiredMixin(EventMemberRequiredMixin):
    """Réservé aux organisateurs de l'événement."""

    def check_membership_permissions(self):
        if not self.membership.is_organizer:
            raise PermissionDenied


class SuperuserRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
