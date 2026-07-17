import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from recruitment.models import Candidate, CandidateNote, JobPosting


@pytest.fixture
def recruiter(db):
    return User.objects.create_user(username="rec", password="pw12345!")


@pytest.fixture
def auth_client(recruiter):
    client = APIClient()
    resp = client.post(
        "/api/auth/login/",
        {"username": "rec", "password": "pw12345!"},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return client


@pytest.fixture
def job(db):
    return JobPosting.objects.create(title="Dev", requirements="Python")


def test_manual_shortlist_sets_flag_and_author(auth_client, job, recruiter):
    cand = Candidate.objects.create(job=job, status=Candidate.Status.REJECTED, score=40)

    resp = auth_client.post(
        f"/api/candidates/{cand.id}/decision/",
        {"decision": "shortlist", "note": "Great culture fit"},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    assert resp.data["status"] == "shortlisted"
    assert resp.data["is_manual_decision"] is True
    assert resp.data["decided_by_name"] == "rec"

    cand.refresh_from_db()
    assert cand.is_manual_decision is True
    assert cand.decided_by == recruiter
    assert cand.decided_at is not None
    # The optional note was recorded.
    assert cand.notes.count() == 1
    assert cand.notes.first().body == "Great culture fit"


def test_reset_decision_reverts_to_ai_score(auth_client, job):
    cand = Candidate.objects.create(
        job=job, status=Candidate.Status.SHORTLISTED, score=40,
        is_manual_decision=True,
    )

    resp = auth_client.post(
        f"/api/candidates/{cand.id}/decision/",
        {"decision": "reset"},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    cand.refresh_from_db()
    assert cand.is_manual_decision is False
    # score 40 < default threshold 70 -> rejected
    assert cand.status == Candidate.Status.REJECTED


def test_apply_score_preserves_manual_decision(job):
    cand = Candidate.objects.create(
        job=job, status=Candidate.Status.SHORTLISTED, score=30,
        is_manual_decision=True,
    )
    # A fresh (low) AI score must not override the human shortlist.
    cand.apply_score(10, "weak on paper")
    assert cand.status == Candidate.Status.SHORTLISTED
    assert cand.score == 10  # score still refreshed


def test_invalid_decision_rejected(auth_client, job):
    cand = Candidate.objects.create(job=job)
    resp = auth_client.post(
        f"/api/candidates/{cand.id}/decision/",
        {"decision": "maybe"},
        format="json",
    )
    assert resp.status_code == 400


def test_add_and_list_notes(auth_client, job, recruiter):
    cand = Candidate.objects.create(job=job)

    post = auth_client.post(
        f"/api/candidates/{cand.id}/notes/",
        {"body": "Called candidate, available in 2 weeks"},
        format="json",
    )
    assert post.status_code == 201, post.content
    assert post.data["author_name"] == "rec"

    listing = auth_client.get(f"/api/candidates/{cand.id}/notes/")
    assert listing.status_code == 200
    assert len(listing.data) == 1
    assert CandidateNote.objects.filter(candidate=cand).count() == 1


def test_empty_note_rejected(auth_client, job):
    cand = Candidate.objects.create(job=job)
    resp = auth_client.post(
        f"/api/candidates/{cand.id}/notes/",
        {"body": "   "},
        format="json",
    )
    assert resp.status_code == 400


def test_job_stats(auth_client, job):
    Candidate.objects.create(
        job=job, status=Candidate.Status.SHORTLISTED, score=90,
        skills=["Python", "django"],
    )
    Candidate.objects.create(
        job=job, status=Candidate.Status.REJECTED, score=40,
        skills=["python", "React"],
    )
    Candidate.objects.create(job=job, status=Candidate.Status.PENDING)

    resp = auth_client.get(f"/api/jobs/{job.id}/stats/")
    assert resp.status_code == 200, resp.content
    data = resp.data
    assert data["total"] == 3
    assert data["by_status"]["shortlisted"] == 1
    assert data["processing"] == 1
    assert data["score_summary"]["count"] == 2
    assert data["score_summary"]["average"] == 65.0
    assert data["score_summary"]["max"] == 90.0
    # "python" appears on two candidates (case-insensitive) -> top skill.
    assert data["top_skills"][0] == {"skill": "python", "count": 2}


def test_job_export_csv(auth_client, job):
    Candidate.objects.create(
        job=job, name="Ada Lovelace", email="ada@example.com",
        status=Candidate.Status.SHORTLISTED, score=88, skills=["Python"],
    )
    resp = auth_client.get(f"/api/jobs/{job.id}/export/")
    assert resp.status_code == 200
    assert resp["Content-Type"] == "text/csv"
    assert "attachment; filename=" in resp["Content-Disposition"]
    body = resp.content.decode()
    assert "Ada Lovelace" in body
    assert "Shortlisted" in body
