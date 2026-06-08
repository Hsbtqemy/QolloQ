from django.dispatch import receiver

from allauth.account.signals import password_changed, password_reset


@receiver(password_changed)
@receiver(password_reset)
def clear_must_change_password(request, user, **kwargs):
    if getattr(user, "must_change_password", False):
        user.must_change_password = False
        user.save(update_fields=["must_change_password"])
