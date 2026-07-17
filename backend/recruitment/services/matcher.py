"""
Candidate-to-job matching via the OpenAI API.

Given parsed resume data and a job's requirements, ask the model for a 0-100
match score and a short justification. Returns a normalized dict; raises
MatchError on hard failures so the caller (Celery task) can retry.
"""
from __future__ import annotations

import json
import logging

from django.conf import settings

logger = logging.getLogger("recruitment")

SYSTEM_PROMPT = (
    "You are an experienced technical recruiter. You evaluate how well a "
    "candidate fits a specific job based only on the structured resume data "
    "and the job requirements provided. Be objective and concise. "
    "Return a match score from 0 to 100 where 100 is a perfect fit, and a "
    "one-to-three sentence justification. Respond ONLY with JSON matching "
    'this schema: {"score": <number 0-100>, "justification": <string>}.'
)


class MatchError(Exception):
    """Raised when a usable score could not be obtained from the model."""


def score_candidate(*, job, parsed: dict) -> dict:
    """Return {"score": float, "justification": str} for a candidate/job pair.

    `job` is a JobPosting instance; `parsed` is the normalized resume dict.
    """
    if not settings.OPENAI_API_KEY:
        raise MatchError("OPENAI_API_KEY is not configured")

    user_prompt = _build_user_prompt(job, parsed)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = response.choices[0].message.content
    except Exception as exc:  # noqa: BLE001 - network / SDK / rate-limit errors
        logger.error("OpenAI request failed: %s", exc)
        raise MatchError(str(exc)) from exc

    return _parse_response(content)


def _build_user_prompt(job, parsed: dict) -> str:
    payload = {
        "job": {
            "title": job.title,
            "department": job.department,
            "requirements": job.requirements,
            "description": job.description,
        },
        "candidate": {
            "name": parsed.get("name"),
            "skills": parsed.get("skills"),
            "total_experience_years": parsed.get("total_experience_years"),
            "experience": parsed.get("experience"),
            "education": parsed.get("education"),
        },
    }
    return (
        "Evaluate this candidate against the job requirements.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def _parse_response(content: str | None) -> dict:
    if not content:
        raise MatchError("Empty response from model")
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise MatchError(f"Model did not return valid JSON: {content!r}") from exc

    try:
        score = float(data["score"])
    except (KeyError, TypeError, ValueError) as exc:
        raise MatchError(f"Missing/invalid score in response: {data!r}") from exc

    score = max(0.0, min(100.0, score))
    justification = str(data.get("justification", "")).strip()
    return {"score": score, "justification": justification}
