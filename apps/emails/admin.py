from django.contrib import admin

from .models import EmailCampaign


@admin.register(EmailCampaign)
class EmailCampaignAdmin(admin.ModelAdmin):
    list_display = ["subject", "event", "audience", "is_sent", "sent_count", "created_at"]
    list_filter = ["audience", "event"]
    search_fields = ["subject"]
    readonly_fields = ["sent_at", "sent_count", "created_at", "updated_at"]
    raw_id_fields = ["event"]
