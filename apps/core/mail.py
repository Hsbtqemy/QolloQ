import logging
from email.utils import parseaddr

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def send_template_email(
    to: str, subject: str, template_base: str, context: dict, *, event=None
) -> None:
    """Envoie un email HTML + texte brut à partir d'un nom de template de base."""
    context.setdefault("site_url", settings.SITE_URL)
    if event:
        _, addr = parseaddr(settings.DEFAULT_FROM_EMAIL)
        from_email = f"{event.name} <{addr or settings.DEFAULT_FROM_EMAIL}>"
    else:
        from_email = settings.DEFAULT_FROM_EMAIL
    txt = render_to_string(f"emails/{template_base}.txt", context)
    html = render_to_string(f"emails/{template_base}.html", context)
    msg = EmailMultiAlternatives(subject, txt, from_email, [to])
    msg.attach_alternative(html, "text/html")
    msg.send()
