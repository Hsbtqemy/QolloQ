from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View

from apps.core.mixins import CommitteeRequiredMixin, OrganizerRequiredMixin
from apps.core.utils import file_response

from .forms import EventDocumentForm
from .models import EventDocument


def annotate_documents(documents, event_slug):
    """Ajoute download_url et delete_url sur chaque document pour le template."""
    for doc in documents:
        doc.download_url = reverse(
            "documents:download",
            kwargs={"event_slug": event_slug, "doc_id": doc.pk},
        )
        doc.delete_url = reverse(
            "documents:delete",
            kwargs={"event_slug": event_slug, "doc_id": doc.pk},
        )
    return documents


class DocumentCreateView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug):
        form = EventDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.event = self.event
            doc.uploaded_by = request.user
            doc.save()
            messages.success(request, f"Document « {doc.name} » ajouté.")
        else:
            error_text = " ".join(msg for errors in form.errors.values() for msg in errors)
            messages.error(request, f"Impossible d'ajouter le document : {error_text}")
        return redirect("events:detail", event_slug=event_slug)


class DocumentDeleteView(OrganizerRequiredMixin, View):
    def post(self, request, event_slug, doc_id):
        doc = get_object_or_404(EventDocument, pk=doc_id, event=self.event)
        name = doc.name
        doc.delete()
        messages.success(request, f"Document « {name} » supprimé.")
        return redirect("events:detail", event_slug=event_slug)


class DocumentDownloadView(CommitteeRequiredMixin, View):
    def get(self, request, event_slug, doc_id):
        doc = get_object_or_404(EventDocument, pk=doc_id, event=self.event)
        if not doc.file:
            raise Http404
        return file_response(doc.file)
