FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps: build tools for some wheels, plus libs used by parsers.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for better layer caching.
COPY requirements.txt requirements-dev.txt ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# spaCy model used by the fallback parser.
RUN python -m spacy download en_core_web_sm

# NLTK corpora that pyresparser / tokenizers may reach for.
RUN python -m nltk.downloader -d /usr/share/nltk_data punkt stopwords words

# Attempt to install pyresparser WITHOUT its dependencies so it doesn't
# downgrade spaCy. It is tried first at runtime and falls back gracefully.
RUN pip install --no-deps pyresparser==1.0.6 || \
    echo "pyresparser install skipped; fallback parser will be used"

ENV NLTK_DATA=/usr/share/nltk_data

COPY . .

# Non-root runtime user.
RUN useradd -m appuser && \
    mkdir -p /app/media /app/staticfiles && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
