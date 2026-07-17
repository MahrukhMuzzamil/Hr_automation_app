# HR Resume Screening

Recruiters upload candidate resumes, tag each to a job posting, and the system
parses the resume, scores it against the job's requirements with an LLM, and
auto-shortlists strong candidates — all asynchronously so uploads never block.

- **Backend:** Django + Django REST Framework, JWT auth
- **Async:** Celery workers + Redis (resume parsing & OpenAI scoring)
- **Data:** PostgreSQL
- **Frontend:** React (Vite) SPA
- **Edge:** Nginx reverse proxy
- **CI/CD:** GitHub Actions → build & push images to AWS ECR

---

## Core flow

1. Recruiter logs in (JWT) and creates a **Job Posting** with free-text
   `requirements`.
2. Recruiter uploads one or more resumes (PDF/DOCX), each tagged to a job.
3. Upload returns immediately; a **Celery task** does the heavy lifting:
   - Parse the resume with **pyresparser**, falling back to a custom
     **spaCy + regex** parser if pyresparser errors or returns nothing.
   - Send the parsed data + the job's requirements to the **OpenAI API** for a
     `0–100` match score and a short justification.
   - Candidates scoring `>= SHORTLIST_THRESHOLD` are auto-marked
     **shortlisted**, others **rejected**.
4. The dashboard shows jobs with applicant/shortlisted counts, and a per-job
   candidate table (name, score, status, resume download) that is
   sortable/filterable by score and status. It live-polls while candidates are
   still processing.

> **Not in v1:** no automatic pulling from LinkedIn/Indeed — resumes come in
> only via manual recruiter upload.

---

## Project layout

```
.
├── docker-compose.yml          # db, redis, backend, celery, frontend, nginx
├── nginx/nginx.conf            # top-level reverse proxy (/api, /admin, SPA)
├── .env.example                # copy to .env
├── backend/
│   ├── config/                 # Django project (settings, celery, urls)
│   ├── accounts/               # recruiter JWT auth + create_recruiter command
│   └── recruitment/
│       ├── models.py           # JobPosting, Candidate
│       ├── serializers.py, views.py, urls.py
│       ├── tasks.py            # Celery pipeline: parse -> score -> shortlist
│       └── services/
│           ├── resume_parser.py  # pyresparser + spaCy fallback
│           └── matcher.py        # OpenAI scoring
├── frontend/                   # React (Vite) SPA + its own nginx for static
└── .github/workflows/ci.yml    # test -> build -> push to ECR
```

---

## Running locally with Docker

```bash
cp .env.example .env
# edit .env: set DJANGO_SECRET_KEY, POSTGRES_PASSWORD, OPENAI_API_KEY

docker compose up --build
```

Then:

```bash
# create a recruiter login
docker compose exec backend python manage.py create_recruiter \
    --username jane --password "s3cret!" --email jane@example.com --staff
```

Open **http://localhost** and sign in.

- App (SPA + API): http://localhost
- Django admin: http://localhost/admin/
- Health check: http://localhost/api/health/

### What each service does

| Service    | Role                                                            |
|------------|----------------------------------------------------------------|
| `db`       | PostgreSQL 16                                                   |
| `redis`    | Celery broker + result backend                                 |
| `backend`  | Gunicorn/Django API; runs migrations & collectstatic on start  |
| `celery`   | Worker that parses resumes and calls OpenAI                     |
| `frontend` | Nginx serving the built React app                              |
| `nginx`    | Reverse proxy: `/api` + `/admin` → backend, everything else → SPA |

Resume downloads are authorized by Django, then streamed by Nginx via
`X-Accel-Redirect` (the `/media/` location is `internal`), so files are never
served without an authenticated request.

---

## Local development without Docker

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python -m spacy download en_core_web_sm

export USE_X_ACCEL_REDIRECT=0   # serve resume files directly (no Nginx)
python manage.py migrate
python manage.py create_recruiter --username jane --password "s3cret!"
python manage.py runserver
# in another shell, with Redis running:
celery -A config worker --loglevel=info
```

**Frontend**

```bash
cd frontend
npm install
npm run dev     # proxies /api to http://localhost:8000
```

Run backend tests:

```bash
cd backend && pytest
```

---

## Configuration (`.env`)

| Variable | Purpose |
|----------|---------|
| `DJANGO_SECRET_KEY` | Django secret |
| `DJANGO_DEBUG` | `0` in prod, `1` in dev |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts |
| `CORS_ALLOWED_ORIGINS` | Browser origins allowed to call the API |
| `POSTGRES_*` | Database connection |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Redis URLs |
| `OPENAI_API_KEY` | Required for scoring |
| `OPENAI_MODEL` | Default `gpt-4o-mini` |
| `SHORTLIST_THRESHOLD` | Score at/above which a candidate is shortlisted (default 70) |
| `USE_X_ACCEL_REDIRECT` | `1` behind Nginx, `0` for direct file serving in dev |

---

## API reference (all under `/api/`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login/` | `{username, password}` → `{access, refresh, user}` |
| POST | `/auth/refresh/` | Rotate access token |
| GET | `/auth/me/` | Current recruiter |
| GET/POST | `/jobs/` | List (with applicant/shortlisted counts) / create |
| GET | `/jobs/{id}/candidates/` | Per-job table; `?status=&min_score=&ordering=` |
| GET | `/jobs/{id}/stats/` | Analytics: status breakdown, score summary, top skills |
| GET | `/jobs/{id}/export/` | Download the job's candidates as CSV |
| POST | `/candidates/upload/` | multipart `job` + `resume` → queues processing |
| POST | `/candidates/{id}/reprocess/` | Re-run parse + score |
| POST | `/candidates/{id}/decision/` | Manual `{decision: shortlist\|reject\|reset, note?}` |
| GET/POST | `/candidates/{id}/notes/` | List / add recruiter notes |
| GET | `/candidates/{id}/resume/` | Download original resume |

### Manual decisions vs. AI scoring

Recruiters can override the AI with a manual **shortlist**/**reject** (or
**reset** back to AI control). A manual decision is sticky: the async pipeline
still refreshes the parsed data and match score on re-processing, but it never
overwrites a human's status (see `Candidate.apply_score` and `tasks.py`).

---

## Note on `pyresparser`

`pyresparser` pins an old spaCy (`<3`) and is brittle across environments. To
keep the image on modern spaCy 3.x, it is installed with `--no-deps` and tried
**first** at runtime; if it raises or returns nothing, the code transparently
falls back to the custom spaCy 3.x + regex parser in
[`services/resume_parser.py`](backend/recruitment/services/resume_parser.py).
Both paths return the same normalized shape, so scoring is unaffected by which
parser ran (`Candidate.parser_used` records which one did).

---

## CI/CD

`.github/workflows/ci.yml`:

1. **backend-tests** — spins up Postgres, runs migrations check + `pytest`.
2. **frontend-build** — `npm install && npm run build`.
3. **build-and-push** (on push to `main`) — assumes an AWS role via OIDC, logs
   into ECR, and builds/pushes `hr-app-backend` and `hr-app-frontend` images
   tagged `latest` and the commit SHA.
4. **deploy** — placeholder, commented out until an AWS host is provisioned.

Required repository secrets: `AWS_ROLE_ARN`, `AWS_REGION`. The two ECR
repositories (`hr-app-backend`, `hr-app-frontend`) must exist beforehand.
