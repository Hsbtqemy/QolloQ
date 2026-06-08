from django.contrib import admin

from .models import LogisticsField, LogisticsFieldResponse, LogisticsForm, LogisticsResponse


class LogisticsFieldInline(admin.TabularInline):
    model = LogisticsField
    extra = 0
    fields = ["label", "kind", "required", "order"]
    ordering = ["order"]


@admin.register(LogisticsForm)
class LogisticsFormAdmin(admin.ModelAdmin):
    list_display = ["name", "event", "is_open", "deadline"]
    list_filter = ["is_open"]
    raw_id_fields = ["event"]
    inlines = [LogisticsFieldInline]


class LogisticsFieldResponseInline(admin.TabularInline):
    model = LogisticsFieldResponse
    extra = 0
    fields = ["field", "value"]
    readonly_fields = ["field"]


@admin.register(LogisticsResponse)
class LogisticsResponseAdmin(admin.ModelAdmin):
    list_display = ["respondent_name", "respondent_email", "form", "is_complete", "created_at"]
    list_filter = ["is_complete", "form__event"]
    search_fields = ["respondent_name", "respondent_email"]
    raw_id_fields = ["form"]
    readonly_fields = ["token", "created_at", "updated_at"]
    inlines = [LogisticsFieldResponseInline]
