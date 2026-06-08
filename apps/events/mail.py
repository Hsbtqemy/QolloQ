from apps.core.mail import send_template_email
from apps.events.models import Membership


def send_member_invitation(user, event, role, invitation_url):
    role_label = dict(Membership.Role.choices).get(role, role)
    send_template_email(
        to=user.email,
        subject=f"Invitation — {event.name}",
        template_base="member_invitation",
        context={
            "user": user,
            "event": event,
            "role_label": role_label,
            "invitation_url": invitation_url,
            "is_new_account": not user.has_usable_password(),
        },
        event=event,
    )
