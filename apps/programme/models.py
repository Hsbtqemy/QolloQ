from django.db import models

from apps.core.models import BaseModel
from apps.events.models import Event
from apps.submissions.models import Proposal


class Session(BaseModel):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="sessions",
        verbose_name="Événement",
    )
    date = models.DateField(verbose_name="Jour")
    start_time = models.TimeField(null=True, blank=True, verbose_name="Début")
    end_time = models.TimeField(null=True, blank=True, verbose_name="Fin")
    location = models.CharField(max_length=255, blank=True, verbose_name="Salle / lieu")
    title = models.CharField(max_length=500, blank=True, verbose_name="Intitulé de la session")
    moderator = models.CharField(max_length=255, blank=True, verbose_name="Modérateur·ice")
    order = models.PositiveSmallIntegerField(default=0, verbose_name="Ordre")

    class Meta:
        verbose_name = "Session"
        verbose_name_plural = "Sessions"
        ordering = ["date", "order", "start_time"]

    def __str__(self):
        label = self.title or (f"Session {self.start_time:%H:%M}" if self.start_time else "Session sans titre")
        return f"{self.date:%d/%m} — {label}"

    @property
    def duration_minutes(self):
        if not self.start_time or not self.end_time:
            return None
        start = self.start_time.hour * 60 + self.start_time.minute
        end = self.end_time.hour * 60 + self.end_time.minute
        return max(0, end - start)


class Communication(models.Model):
    class Kind(models.TextChoices):
        TALK = "talk", "Communication"
        QA = "qa", "Questions/Réponses"
        DISCUSSION = "discussion", "Discussion"
        INTRO = "intro", "Introduction"

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="communications",
        verbose_name="Session",
    )
    proposal = models.OneToOneField(
        Proposal,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="communication",
        verbose_name="Proposition liée",
    )
    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        default=Kind.TALK,
        verbose_name="Type",
    )
    title = models.CharField(max_length=500, verbose_name="Titre")
    speaker_name = models.CharField(max_length=255, blank=True, verbose_name="Intervenant·e")
    duration = models.PositiveSmallIntegerField(default=20, verbose_name="Durée (min)")
    order = models.PositiveSmallIntegerField(default=0, verbose_name="Ordre")

    class Meta:
        verbose_name = "Communication"
        verbose_name_plural = "Communications"
        ordering = ["order"]

    def __str__(self):
        return self.title


class AnnexEvent(BaseModel):
    class Kind(models.TextChoices):
        BREAK = "break", "Pause"
        MEAL = "meal", "Repas"
        PLENARY = "plenary", "Plénière"
        CULTURAL = "cultural", "Événement culturel"
        OTHER = "other", "Autre"

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="annex_events",
        verbose_name="Événement",
    )
    date = models.DateField(verbose_name="Jour")
    start_time = models.TimeField(verbose_name="Début")
    end_time = models.TimeField(verbose_name="Fin")
    label = models.CharField(max_length=255, verbose_name="Intitulé")
    description = models.TextField(blank=True, verbose_name="Description")
    kind = models.CharField(
        max_length=10,
        choices=Kind.choices,
        default=Kind.OTHER,
        verbose_name="Type",
    )
    order = models.PositiveSmallIntegerField(default=0, verbose_name="Ordre")

    class Meta:
        verbose_name = "Événement annexe"
        verbose_name_plural = "Événements annexes"
        ordering = ["date", "order", "start_time"]

    @property
    def duration_minutes(self):
        start = self.start_time.hour * 60 + self.start_time.minute
        end = self.end_time.hour * 60 + self.end_time.minute
        return max(0, end - start)

    def __str__(self):
        return f"{self.date:%d/%m} {self.start_time:%H:%M} — {self.label}"
