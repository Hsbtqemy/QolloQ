from django.http import HttpResponse
from django.views import View

from apps.core.mixins import OrganizerRequiredMixin

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
