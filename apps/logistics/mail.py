from django.urls import reverse

from apps.core.mail import send_template_email


def send_logistics_link(response, request=None):
    """Envoie le lien d'accès au formulaire logistique à un intervenant."""
    token_url = reverse("logistics:respond", kwargs={"token": str(response.token)})
    if request:
        token_url = request.build_absolute_uri(token_url)

    send_template_email(
        to=response.respondent_email,
        subject=f"Formulaire logistique — {response.form.event.name}",
        template_base="logistics/email_link",
        context={
            "response": response,
            "logistics_form": response.form,
            "event": response.form.event,
            "token_url": token_url,
        },
        event=response.form.event,
    )
