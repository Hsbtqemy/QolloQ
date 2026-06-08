from django.contrib import admin

from .models import Event, Membership


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 1
    autocomplete_fields = ["user"]


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["name", "start_date", "end_date", "location", "submissions_open"]
    list_filter = ["submissions_open", "double_blind"]
    search_fields = ["name", "location"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [MembershipInline]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "event", "role"]
    list_filter = ["role"]
    autocomplete_fields = ["user"]
