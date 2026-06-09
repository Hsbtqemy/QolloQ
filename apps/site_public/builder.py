import io
import os
import zipfile

from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from apps.programme.views import _build_programme_context
from apps.submissions.models import Proposal


def build_site_zip(event, request):
    speakers = list(
        Proposal.objects.filter(event=event, status=Proposal.Status.ACCEPTED)
        .prefetch_related("authors")
        .order_by("title")
    )

    prog_ctx = _build_programme_context(event)

    submission_url = None
    deadline = event.submission_deadline
    if event.submissions_open and (not deadline or deadline >= timezone.now()):
        submission_url = request.build_absolute_uri(
            reverse("submissions:public_submit", kwargs={"event_slug": event.slug})
        )

    banner_zip = None
    if event.banner:
        ext = os.path.splitext(event.banner.name)[1].lower() or ".jpg"
        banner_zip = f"images/banner{ext}"

    ctx = {
        "event": event,
        "speakers": speakers,
        "submission_url": submission_url,
        "banner_zip": banner_zip,
        **prog_ctx,
    }

    pages = [
        ("index.html",       "site_public/index.html"),
        ("appel.html",       "site_public/appel.html"),
        ("programme.html",   "site_public/programme.html"),
        ("intervenants.html","site_public/speakers.html"),
    ]

    css_path = settings.BASE_DIR / "static/css/site_public.css"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, template_name in pages:
            zf.writestr(filename, render_to_string(template_name, ctx))
        if css_path.exists():
            zf.write(str(css_path), "css/style.css")
        if banner_zip and event.banner:
            try:
                with event.banner.open("rb") as img:
                    zf.writestr(banner_zip, img.read())
            except (OSError, ValueError):
                pass
    buf.seek(0)
    return buf
