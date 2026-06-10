import logging
from email.utils import formataddr, parseaddr

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import Context, Template
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def send_template_email(
    to: str, subject: str, template_base: str, context: dict, *, event=None
) -> None:
    """Envoie un email HTML + texte brut à partir d'un nom de template de base."""
    context.setdefault("site_url", settings.SITE_URL)

    # Charge le corps depuis la base si un EmailTemplate existe pour cette clé.
    tmpl_key = template_base.replace("/", "_")
    try:
        from apps.emails.models import EmailTemplate
        db_tmpl = EmailTemplate.objects.get(key=tmpl_key)
        ctx = Context(context)
        if db_tmpl.subject_fr:
            subject = Template(db_tmpl.subject_fr).render(ctx)
        context["email_body_fr"] = Template(db_tmpl.body_fr).render(ctx)
        context["email_body_en"] = (
            Template(db_tmpl.body_en).render(ctx) if db_tmpl.body_en else ""
        )
    except Exception:
        logger.warning("EmailTemplate lookup/render failed for key '%s'", tmpl_key, exc_info=True)
        context.setdefault("email_body_fr", "")
        context.setdefault("email_body_en", "")

    if event:
        _, addr = parseaddr(settings.DEFAULT_FROM_EMAIL)
        display_name = event.from_name or event.name
        from_email = formataddr((display_name, addr or settings.DEFAULT_FROM_EMAIL))
    else:
        from_email = settings.DEFAULT_FROM_EMAIL
    txt = render_to_string(f"emails/{template_base}.txt", context)
    html = render_to_string(f"emails/{template_base}.html", context)
    msg = EmailMultiAlternatives(subject, txt, from_email, [to])
    msg.attach_alternative(html, "text/html")
    msg.send()
