import os
import uuid

from django.conf import settings
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone


def resume_upload_path(instance, filename):
    """Store resumes under media/resumes/<job_id>/<uuid>.<ext>."""
    ext = os.path.splitext(filename)[1].lower()
    return f"resumes/{instance.job_id}/{uuid.uuid4().hex}{ext}"


class JobPosting(models.Model):
    title = models.CharField(max_length=255)
    department = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    # Free-text requirements fed to the LLM alongside parsed resume data.
    requirements = models.TextField(
        help_text="Key skills, experience and qualifications used for scoring."
    )
    is_open = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_postings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @classmethod
    def with_counts(cls):
        """Annotate applicant and shortlisted counts for dashboard lists."""
        return cls.objects.annotate(
            applicant_count=Count("candidates", distinct=True),
            shortlisted_count=Count(
                "candidates",
                filter=Q(candidates__status=Candidate.Status.SHORTLISTED),
                distinct=True,
            ),
        ).order_by("-created_at")


class Candidate(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SHORTLISTED = "shortlisted", "Shortlisted"
        REJECTED = "rejected", "Rejected"
        FAILED = "failed", "Failed"

    job = models.ForeignKey(
        JobPosting, on_delete=models.CASCADE, related_name="candidates"
    )
    resume = models.FileField(upload_to=resume_upload_path)
    original_filename = models.CharField(max_length=255, blank=True)

    # --- Parsed fields (populated asynchronously) ---
    name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=64, blank=True)
    skills = models.JSONField(default=list, blank=True)
    experience = models.JSONField(default=list, blank=True)
    education = models.JSONField(default=list, blank=True)
    total_experience_years = models.FloatField(null=True, blank=True)
    raw_parsed = models.JSONField(default=dict, blank=True)
    parser_used = models.CharField(max_length=32, blank=True)

    # --- Scoring (populated by the OpenAI matcher) ---
    score = models.FloatField(null=True, blank=True)
    justification = models.TextField(blank=True)

    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    error_message = models.TextField(blank=True)

    # --- Manual recruiter override ---
    # When a recruiter shortlists/rejects by hand, we record it so the async
    # re-scoring pipeline never clobbers a human decision.
    is_manual_decision = models.BooleanField(default=False)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="candidate_decisions",
    )
    decided_at = models.DateTimeField(null=True, blank=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_candidates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-score", "-created_at"]
        indexes = [
            models.Index(fields=["job", "status"]),
            models.Index(fields=["job", "-score"]),
        ]

    def __str__(self):
        return f"{self.name or self.original_filename} ({self.job.title})"

    def apply_score(self, score, justification):
        """Store the score/justification and auto-shortlist/reject.

        A human decision always wins: if the candidate was manually
        shortlisted/rejected we still record the fresh score and reasoning but
        leave the recruiter's status untouched.
        """
        self.score = score
        self.justification = justification
        if self.is_manual_decision:
            return
        threshold = settings.SHORTLIST_THRESHOLD
        self.status = (
            self.Status.SHORTLISTED if score >= threshold else self.Status.REJECTED
        )

    def set_manual_decision(self, *, user, status):
        """Record a recruiter's manual shortlist/reject decision."""
        self.status = status
        self.is_manual_decision = True
        self.decided_by = user if user and user.is_authenticated else None
        self.decided_at = timezone.now()

    def clear_manual_decision(self):
        """Drop the manual flag so AI scoring governs status again.

        Re-derives status from the existing score if one is present.
        """
        self.is_manual_decision = False
        self.decided_by = None
        self.decided_at = None
        if self.score is not None:
            threshold = settings.SHORTLIST_THRESHOLD
            self.status = (
                self.Status.SHORTLISTED
                if self.score >= threshold
                else self.Status.REJECTED
            )


class CandidateNote(models.Model):
    """A free-text note a recruiter leaves on a candidate."""

    candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE, related_name="notes"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="candidate_notes",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note on {self.candidate_id} by {self.author_id}"
