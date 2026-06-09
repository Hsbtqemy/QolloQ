from django.contrib import admin

from .models import BudgetCharge, BudgetDocument, BudgetLine, BudgetSettings, LogisticsField, LogisticsFieldResponse, LogisticsForm, LogisticsResponse


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



@admin.register(BudgetSettings)
class BudgetSettingsAdmin(admin.ModelAdmin):
    list_display = ["event", "envelope"]
    raw_id_fields = ["event"]


class BudgetDocumentInline(admin.TabularInline):
    model = BudgetDocument
    extra = 0
    fields = ["label", "kind", "file", "amount"]


class BudgetChargeInline(admin.TabularInline):
    model = BudgetCharge
    extra = 0
    fields = ["person_name", "person_email", "description", "amount", "status"]


@admin.register(BudgetLine)
class BudgetLineAdmin(admin.ModelAdmin):
    list_display = ["label", "category", "amount_planned", "amount_actual", "event"]
    list_filter = ["category", "event"]
    search_fields = ["label"]
    raw_id_fields = ["event"]
    inlines = [BudgetDocumentInline, BudgetChargeInline]


@admin.register(BudgetCharge)
class BudgetChargeAdmin(admin.ModelAdmin):
    list_display = ["person_name", "description", "amount", "status", "budget_line"]
    list_filter = ["status", "budget_line__event"]
    search_fields = ["person_name", "person_email", "description"]
    raw_id_fields = ["budget_line", "form_response"]
