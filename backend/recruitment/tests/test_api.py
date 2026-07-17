import io

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from recruitment.models import Candidate, JobPosting


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
    token = resp.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def test_login_returns_user(auth_client):
    resp = auth_client.get("/api/auth/me/")
    assert resp.status_code == 200
    assert resp.data["username"] == "rec"


def test_unauthenticated_jobs_blocked():
    resp = APIClient().get("/api/jobs/")
    assert resp.status_code == 401


def test_job_counts(auth_client, db):
    job = JobPosting.objects.create(title="Dev", requirements="Python")
    Candidate.objects.create(job=job, status=Candidate.Status.SHORTLISTED, score=90)
    Candidate.objects.create(job=job, status=Candidate.Status.REJECTED, score=30)

    resp = auth_client.get("/api/jobs/")
    assert resp.status_code == 200
    row = resp.data["results"][0]
    assert row["applicant_count"] == 2
    assert row["shortlisted_count"] == 1


def test_upload_queues_processing(auth_client, db, monkeypatch):
    job = JobPosting.objects.create(title="Dev", requirements="Python")
    called = {}

    def fake_delay(candidate_id):
        called["id"] = candidate_id

    monkeypatch.setattr(
        "recruitment.views.process_candidate_resume.delay", fake_delay
    )

    upload = io.BytesIO(b"%PDF-1.4 fake resume")
    upload.name = "resume.pdf"
    resp = auth_client.post(
        "/api/candidates/upload/",
        {"job": job.id, "resume": upload},
        format="multipart",
    )
    assert resp.status_code == 201, resp.content
    assert called["id"] == resp.data["id"]
    assert Candidate.objects.count() == 1


def test_upload_rejects_bad_extension(auth_client, db):
    job = JobPosting.objects.create(title="Dev", requirements="Python")
    upload = io.BytesIO(b"nope")
    upload.name = "resume.txt"
    resp = auth_client.post(
        "/api/candidates/upload/",
        {"job": job.id, "resume": upload},
        format="multipart",
    )
    assert resp.status_code == 400
