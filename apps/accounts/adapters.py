from allauth.account.adapter import DefaultAccountAdapter


class NoSignupAccountAdapter(DefaultAccountAdapter):
    """Inscription publique désactivée — comptes créés via l'admin Django."""

    def is_open_for_signup(self, request):
        return False

    def get_client_ip(self, request):
        ip = request.META.get("HTTP_X_REAL_IP")
        if not ip:
            forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
            ip = forwarded.split(",")[0].strip()
        if not ip:
            ip = request.META.get("REMOTE_ADDR", "")
        if not ip:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Unable to determine client IP address")
        return ip
