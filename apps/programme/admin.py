from django.contrib import admin

from .models import AnnexEvent, Communication, Session


class CommunicationInline(admin.TabularInline):
    model = Communication
    extra = 0
    fields = ["title", "speaker_name", "duration", "order", "proposal"]


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ["event", "date", "start_time", "end_time", "location", "title"]
    list_filter = ["event", "date"]
    inlines = [CommunicationInline]


@admin.register(AnnexEvent)
class AnnexEventAdmin(admin.ModelAdmin):
    list_display = ["event", "date", "start_time", "end_time", "label", "kind"]
    list_filter = ["event", "kind"]
