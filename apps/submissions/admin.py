from django.contrib import admin

from .models import Author, Evaluation, Proposal


class AuthorInline(admin.TabularInline):
    model = Author
    extra = 1


class EvaluationInline(admin.TabularInline):
    model = Evaluation
    extra = 0
    readonly_fields = ["evaluator", "verdict", "comment"]
    can_delete = False


@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = ["title", "event", "status", "submitter_email", "created_at"]
    list_filter = ["status", "event"]
    search_fields = ["title", "submitter_email"]
    readonly_fields = ["token"]
    inlines = [AuthorInline, EvaluationInline]


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ["proposal", "evaluator", "verdict", "created_at"]
    list_filter = ["verdict"]
