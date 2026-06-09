from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views import View

from apps.core.mixins import OrganizerRequiredMixin
from apps.events.models import CallVersion, Event

from .builder import build_site_zip


class SitePublishView(OrganizerRequiredMixin, View):
    """Génère et télécharge le site public sous forme de ZIP autonome."""

    def post(self, request, event_slug):
        buf = build_site_zip(self.event, request)
        response = HttpResponse(buf.read(), content_type="application/zip")
        response["Content-Disposition"] = (
            f'attachment; filename="site-{self.event.slug}.zip"'
        )
        return response


class EventPublicView(View):
    """Page publique en ligne de l'événement (sans compte requis)."""

    def get(self, request, event_slug):
        event = get_object_or_404(Event, slug=event_slug)
        versions = list(event.call_versions.all())

        lang = request.GET.get("lang", "")
        active_version = None
        if versions:
            if lang:
                active_version = next((v for v in versions if v.language == lang), versions[0])
            else:
                active_version = next((v for v in versions if v.language == "fr"), versions[0])

        submit_url = None
        deadline = event.submission_deadline
        if event.submissions_open and (not deadline or deadline >= timezone.now()):
            submit_url = request.build_absolute_uri(
                reverse("submissions:public_submit", kwargs={"event_slug": event_slug})
            )
        return render(request, "site_public/page.html", {
            "event": event,
            "versions": versions,
            "active_version": active_version,
            "submit_url": submit_url,
        })


class EventCallPDFView(View):
    """Téléchargement de l'appel à communications en PDF (WeasyPrint)."""

    def get(self, request, event_slug, lang):
        event = get_object_or_404(Event, slug=event_slug)
        version = get_object_or_404(CallVersion, event=event, language=lang)
        html_string = render_to_string(
            "site_public/call_pdf.html",
            {"event": event, "version": version},
            request=request,
        )
        try:
            from weasyprint import HTML as WeasyHTML  # import lazy — dépend de Pango
            pdf = WeasyHTML(
                string=html_string, base_url=request.build_absolute_uri("/")
            ).write_pdf()
        except OSError:
            return HttpResponse(
                "Génération PDF indisponible (bibliothèques système manquantes).",
                status=503,
                content_type="text/plain",
            )
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="appel-{event.slug}-{lang}.pdf"'
        )
        return response
