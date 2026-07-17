"""
Async resume-processing pipeline.

`process_candidate_resume` is queued right after a recruiter uploads a resume.
It parses the file, scores it against the job via OpenAI, and updates status.
Kept idempotent-ish so a retry re-runs the full pipeline safely.
"""
import logging

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from .models import Candidate
from .services.matcher import MatchError, score_candidate
from .services.resume_parser import parse_resume

logger = logging.getLogger("recruitment")


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def process_candidate_resume(self, candidate_id: int):
    try:
        candidate = Candidate.objects.select_related("job").get(pk=candidate_id)
    except Candidate.DoesNotExist:
        logger.warning("Candidate %s no longer exists; skipping", candidate_id)
        return

    candidate.status = Candidate.Status.PROCESSING
    candidate.error_message = ""
    candidate.save(update_fields=["status", "error_message", "updated_at"])

    try:
        # 1) Parse the resume file.
        parsed = parse_resume(candidate.resume.path)
        _apply_parsed(candidate, parsed)

        # 2) Score against the job requirements via OpenAI.
        result = score_candidate(job=candidate.job, parsed=parsed.as_dict())
        candidate.apply_score(result["score"], result["justification"])
        candidate.save()
        logger.info(
            "Candidate %s scored %.1f -> %s",
            candidate_id, candidate.score, candidate.status,
        )
    except MatchError as exc:
        # OpenAI/transient failure: retry a few times, then mark failed.
        logger.warning("Scoring failed for candidate %s: %s", candidate_id, exc)
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            _mark_failed(candidate, f"Scoring failed: {exc}")
    except SoftTimeLimitExceeded:
        _mark_failed(candidate, "Processing timed out")
    except Exception as exc:  # noqa: BLE001 - parsing/unexpected failures
        logger.exception("Unexpected error processing candidate %s", candidate_id)
        _mark_failed(candidate, f"Processing error: {exc}")


def _apply_parsed(candidate: Candidate, parsed) -> None:
    candidate.name = parsed.name or candidate.name
    candidate.email = parsed.email
    candidate.phone = parsed.phone
    candidate.skills = parsed.skills
    candidate.experience = parsed.experience
    candidate.education = parsed.education
    candidate.total_experience_years = parsed.total_experience_years
    candidate.parser_used = parsed.parser_used
    candidate.raw_parsed = parsed.raw
    candidate.save()


def _mark_failed(candidate: Candidate, message: str) -> None:
    candidate.status = Candidate.Status.FAILED
    candidate.error_message = message
    candidate.save(update_fields=["status", "error_message", "updated_at"])
