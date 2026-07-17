from django.contrib import admin

from .models import Candidate, CandidateNote, JobPosting


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ("title", "department", "location", "is_open", "created_at")
    list_filter = ("is_open", "department")
    search_fields = ("title", "department", "location")


class CandidateNoteInline(admin.TabularInline):
    model = CandidateNote
    extra = 0
    readonly_fields = ("author", "created_at")


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = (
        "name", "job", "score", "status", "is_manual_decision",
        "parser_used", "created_at",
    )
    list_filter = ("status", "is_manual_decision", "job", "parser_used")
    search_fields = ("name", "email")
    readonly_fields = ("raw_parsed", "created_at", "updated_at", "decided_at")
    inlines = [CandidateNoteInline]


@admin.register(CandidateNote)
class CandidateNoteAdmin(admin.ModelAdmin):
    list_display = ("candidate", "author", "created_at")
    search_fields = ("candidate__name", "body")
