import os

from rest_framework import serializers

from .models import Candidate, CandidateNote, JobPosting

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}
MAX_RESUME_BYTES = 15 * 1024 * 1024  # 15 MB


class JobPostingSerializer(serializers.ModelSerializer):
    applicant_count = serializers.IntegerField(read_only=True)
    shortlisted_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = JobPosting
        fields = (
            "id", "title", "department", "location", "description",
            "requirements", "is_open", "applicant_count", "shortlisted_count",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class CandidateNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(
        source="author.username", read_only=True, default=None
    )

    class Meta:
        model = CandidateNote
        fields = ("id", "candidate", "body", "author_name", "created_at")
        read_only_fields = ("id", "candidate", "author_name", "created_at")

    def validate_body(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Note cannot be empty.")
        return value


class CandidateSerializer(serializers.ModelSerializer):
    resume_url = serializers.SerializerMethodField()
    decided_by_name = serializers.CharField(
        source="decided_by.username", read_only=True, default=None
    )

    class Meta:
        model = Candidate
        fields = (
            "id", "job", "name", "email", "phone", "skills", "experience",
            "education", "total_experience_years", "score", "justification",
            "status", "parser_used", "error_message", "original_filename",
            "resume_url", "is_manual_decision", "decided_by_name", "decided_at",
            "created_at", "updated_at",
        )
        read_only_fields = fields

    def get_resume_url(self, obj):
        request = self.context.get("request")
        url = f"/api/candidates/{obj.id}/resume/"
        return request.build_absolute_uri(url) if request else url


class CandidateListSerializer(serializers.ModelSerializer):
    """Lighter payload for the per-job candidate table."""

    class Meta:
        model = Candidate
        fields = (
            "id", "name", "email", "score", "status",
            "total_experience_years", "parser_used", "is_manual_decision",
            "created_at",
        )
        read_only_fields = fields


class DecisionSerializer(serializers.Serializer):
    """Input for the manual shortlist/reject/reset decision endpoint."""

    DECISION_CHOICES = ("shortlist", "reject", "reset")

    decision = serializers.ChoiceField(choices=DECISION_CHOICES)
    note = serializers.CharField(
        required=False, allow_blank=True, trim_whitespace=True
    )


class ResumeUploadSerializer(serializers.Serializer):
    """Validates a single resume upload tagged to a job."""

    job = serializers.PrimaryKeyRelatedField(queryset=JobPosting.objects.all())
    resume = serializers.FileField()

    def validate_resume(self, value):
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise serializers.ValidationError(
                f"Unsupported file type '{ext}'. Allowed: PDF, DOCX, DOC."
            )
        if value.size > MAX_RESUME_BYTES:
            raise serializers.ValidationError("Resume exceeds the 15 MB limit.")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        resume = validated_data["resume"]
        return Candidate.objects.create(
            job=validated_data["job"],
            resume=resume,
            original_filename=resume.name,
            uploaded_by=request.user if request.user.is_authenticated else None,
            status=Candidate.Status.PENDING,
        )
