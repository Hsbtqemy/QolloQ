import os
import uuid

from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.events.models import Event


def _event_doc_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"event_documents/{instance.event_id}/{uuid.uuid4().hex}{ext}"


class EventDocument(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name="Événement",
    )
    name = models.CharField(max_length=200, verbose_name="Nom du document")
    description = models.TextField(
        blank=True,
        verbose_name="Description",
        help_text="Optionnel — pour préciser le contenu du document.",
    )
    file = models.FileField(upload_to=_event_doc_upload_to, verbose_name="Fichier")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Ajouté par",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Date d'ajout")

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Document"
        verbose_name_plural = "Documents"

    def __str__(self):
        return self.name


@receiver(post_delete, sender=EventDocument)
def _delete_event_document_file(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)
