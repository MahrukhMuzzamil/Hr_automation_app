from django.contrib import admin

from .models import Candidate, JobPosting


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ("title", "department", "location", "is_open", "created_at")
    list_filter = ("is_open", "department")
    search_fields = ("title", "department", "location")


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ("name", "job", "score", "status", "parser_used", "created_at")
    list_filter = ("status", "job", "parser_used")
    search_fields = ("name", "email")
    readonly_fields = ("raw_parsed", "created_at", "updated_at")
