from django.contrib import admin

from .models import EventDocument


@admin.register(EventDocument)
class EventDocumentAdmin(admin.ModelAdmin):
    list_display = ["name", "event", "uploaded_by", "uploaded_at"]
    list_filter = ["event"]
    search_fields = ["name", "event__name"]
    readonly_fields = ["uploaded_by", "uploaded_at"]
