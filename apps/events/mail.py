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
            "is_bilingual": event.is_bilingual,
        },
        event=event,
    )


def send_committee_invitation(membership, event, eval_link):
    role_label = dict(Membership.Role.choices).get(membership.role, membership.role)
    send_template_email(
        to=membership.email,
        subject=f"Invitation à évaluer — {event.name}",
        template_base="committee_invitation",
        context={
            "membership": membership,
            "event": event,
            "role_label": role_label,
            "eval_link": eval_link,
            "is_bilingual": event.is_bilingual,
        },
        event=event,
    )
