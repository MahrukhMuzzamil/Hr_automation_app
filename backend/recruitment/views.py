import mimetypes
import os

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Candidate, JobPosting
from .serializers import (
    CandidateListSerializer,
    CandidateSerializer,
    JobPostingSerializer,
    ResumeUploadSerializer,
)
from .tasks import process_candidate_resume


class JobPostingViewSet(viewsets.ModelViewSet):
    """CRUD for job postings, annotated with applicant/shortlisted counts."""

    serializer_class = JobPostingSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["is_open", "department"]
    ordering_fields = ["created_at", "title"]
    search_fields = ["title", "department", "location"]

    def get_queryset(self):
        return JobPosting.with_counts()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["get"])
    def candidates(self, request, pk=None):
        """Per-job candidate table: sortable/filterable by score & status."""
        job = self.get_object()
        qs = job.candidates.all()

        status_param = request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        min_score = request.query_params.get("min_score")
        if min_score:
            try:
                qs = qs.filter(score__gte=float(min_score))
            except ValueError:
                pass

        ordering = request.query_params.get("ordering", "-score")
        allowed = {"score", "-score", "created_at", "-created_at", "name", "-name"}
        if ordering in allowed:
            qs = qs.order_by(ordering)

        page = self.paginate_queryset(qs)
        serializer = CandidateListSerializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class CandidateViewSet(viewsets.ReadOnlyModelViewSet):
    """Read candidates plus resume upload and download endpoints."""

    serializer_class = CandidateSerializer
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["job", "status"]
    ordering_fields = ["score", "created_at", "name"]

    def get_queryset(self):
        return Candidate.objects.select_related("job").all()

    @action(detail=False, methods=["post"], url_path="upload")
    def upload(self, request):
        """Upload a resume tagged to a job, then queue async processing."""
        serializer = ResumeUploadSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        candidate = serializer.save()

        # Hand off to Celery so the request returns immediately.
        process_candidate_resume.delay(candidate.id)

        return Response(
            CandidateSerializer(candidate, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="reprocess")
    def reprocess(self, request, pk=None):
        """Re-run parsing + scoring (e.g. after a transient OpenAI failure)."""
        candidate = self.get_object()
        candidate.status = Candidate.Status.PENDING
        candidate.error_message = ""
        candidate.save(update_fields=["status", "error_message", "updated_at"])
        process_candidate_resume.delay(candidate.id)
        return Response({"status": "queued"}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["get"])
    def resume(self, request, pk=None):
        """Download the original resume file.

        In production Nginx streams the file via X-Accel-Redirect after this
        view authorizes the request; in local dev Django serves it directly.
        """
        candidate = self.get_object()
        if not candidate.resume:
            raise Http404("No resume on file")

        filename = candidate.original_filename or os.path.basename(
            candidate.resume.name
        )
        content_type = (
            mimetypes.guess_type(filename)[0] or "application/octet-stream"
        )

        if settings.USE_X_ACCEL_REDIRECT:
            response = HttpResponse(content_type=content_type)
            # candidate.resume.name is like "resumes/<job>/<uuid>.pdf"
            response["X-Accel-Redirect"] = f"/media/{candidate.resume.name}"
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        try:
            return FileResponse(
                candidate.resume.open("rb"),
                as_attachment=True,
                filename=filename,
                content_type=content_type,
            )
        except FileNotFoundError as exc:
            raise Http404("Resume file missing on disk") from exc
