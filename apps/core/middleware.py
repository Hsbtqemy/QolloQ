from django.shortcuts import redirect
from django.urls import reverse


class MustChangePasswordMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and getattr(request.user, "must_change_password", False)
            and request.path not in (
                reverse("account_change_password"),
                reverse("account_logout"),
            )
        ):
            return redirect("account_change_password")
        return self.get_response(request)
