"""
Resume parsing.

Primary path uses `pyresparser`. If that raises for any reason (it is
notoriously brittle across spaCy / NLTK versions and on unusual layouts),
we fall back to a lightweight custom spaCy + regex parser that extracts the
same core fields. Both paths return a normalized dict so downstream code
doesn't care which parser ran.
"""
from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field

logger = logging.getLogger("recruitment")

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(
    r"(\+?\d{1,3}[\s.-]?)?(\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{3,4}"
)

# A compact, extensible skills lexicon for the fallback parser. In production
# this would be backed by a maintained taxonomy / DB table.
SKILL_KEYWORDS = {
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "ruby", "php", "swift", "kotlin", "scala", "r", "matlab",
    "django", "flask", "fastapi", "spring", "react", "angular", "vue",
    "node.js", "express", "next.js", ".net",
    "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
    "jenkins", "git", "ci/cd", "linux",
    "machine learning", "deep learning", "nlp", "pytorch", "tensorflow",
    "scikit-learn", "pandas", "numpy", "spark", "hadoop", "airflow",
    "html", "css", "sass", "graphql", "rest", "grpc", "microservices",
    "agile", "scrum", "jira",
}

DEGREE_KEYWORDS = [
    "phd", "doctorate", "master", "m.sc", "msc", "mba", "bachelor", "b.sc",
    "bsc", "b.tech", "btech", "m.tech", "mtech", "b.e", "b.a", "m.a",
    "associate", "diploma",
]


@dataclass
class ParsedResume:
    name: str = ""
    email: str = ""
    phone: str = ""
    skills: list = field(default_factory=list)
    experience: list = field(default_factory=list)
    education: list = field(default_factory=list)
    total_experience_years: float | None = None
    parser_used: str = ""
    raw: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


def parse_resume(file_path: str) -> ParsedResume:
    """Parse a resume file, trying pyresparser first then the spaCy fallback."""
    try:
        result = _parse_with_pyresparser(file_path)
        if result and (result.name or result.email or result.skills):
            result.parser_used = "pyresparser"
            return result
        logger.warning("pyresparser returned empty result; using fallback")
    except Exception as exc:  # noqa: BLE001 - pyresparser throws many things
        logger.warning("pyresparser failed (%s); using spaCy fallback", exc)

    result = _parse_with_spacy(file_path)
    result.parser_used = "spacy_fallback"
    return result


def _parse_with_pyresparser(file_path: str) -> ParsedResume | None:
    from pyresparser import ResumeParser  # imported lazily; heavy deps

    data = ResumeParser(file_path).get_extracted_data() or {}
    return ParsedResume(
        name=data.get("name") or "",
        email=data.get("email") or "",
        phone=data.get("mobile_number") or "",
        skills=[s for s in (data.get("skills") or []) if s],
        experience=data.get("experience") or [],
        education=_normalize_education(data.get("degree") or data.get("education")),
        total_experience_years=data.get("total_experience"),
        raw=data,
    )


def _parse_with_spacy(file_path: str) -> ParsedResume:
    text = _extract_text(file_path)
    nlp = _get_nlp()

    email = _first(EMAIL_RE.findall(text))
    phone = _extract_phone(text)
    name = _extract_name(text, nlp)
    skills = _extract_skills(text)
    education = _extract_education(text)
    years = _estimate_experience_years(text)

    return ParsedResume(
        name=name,
        email=email,
        phone=phone,
        skills=skills,
        experience=[],
        education=education,
        total_experience_years=years,
        raw={"text_length": len(text)},
    )


# --------------------------------------------------------------------------- #
# Text extraction
# --------------------------------------------------------------------------- #
def _extract_text(file_path: str) -> str:
    lower = file_path.lower()
    if lower.endswith(".pdf"):
        return _extract_pdf_text(file_path)
    if lower.endswith(".docx"):
        return _extract_docx_text(file_path)
    if lower.endswith(".doc"):
        # Best-effort: treat as text; real .doc needs antiword/textract.
        logger.warning("Legacy .doc format has limited support: %s", file_path)
        try:
            return _extract_docx_text(file_path)
        except Exception:  # noqa: BLE001
            return ""
    raise ValueError(f"Unsupported resume format: {file_path}")


def _extract_pdf_text(file_path: str) -> str:
    from pdfminer.high_level import extract_text

    return extract_text(file_path) or ""


def _extract_docx_text(file_path: str) -> str:
    import docx

    document = docx.Document(file_path)
    return "\n".join(p.text for p in document.paragraphs)


# --------------------------------------------------------------------------- #
# Field extractors
# --------------------------------------------------------------------------- #
_NLP = None


def _get_nlp():
    global _NLP
    if _NLP is None:
        import spacy

        try:
            _NLP = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model en_core_web_sm missing; using blank English")
            _NLP = spacy.blank("en")
    return _NLP


def _first(items):
    return items[0] if items else ""


def _extract_phone(text: str) -> str:
    for match in PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", match.group())
        if 7 <= len(digits) <= 15:
            return match.group().strip()
    return ""


def _extract_name(text: str, nlp) -> str:
    # Try the first PERSON entity in the top of the document.
    head = "\n".join(text.strip().splitlines()[:8])
    try:
        doc = nlp(head)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                return ent.text.strip()
    except Exception:  # noqa: BLE001 - blank pipeline has no NER
        pass
    # Fallback: first non-empty line that looks like a name.
    for line in text.strip().splitlines():
        line = line.strip()
        if 2 <= len(line.split()) <= 4 and line.replace(" ", "").isalpha():
            return line
    return ""


def _extract_skills(text: str) -> list:
    lowered = text.lower()
    found = []
    for skill in SKILL_KEYWORDS:
        if re.search(rf"(?<![a-z0-9]){re.escape(skill)}(?![a-z0-9])", lowered):
            found.append(skill)
    return sorted(set(found))


def _normalize_education(value) -> list:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if v]
    return [str(value)]


def _extract_education(text: str) -> list:
    education = []
    for line in text.splitlines():
        low = line.lower()
        if any(deg in low for deg in DEGREE_KEYWORDS):
            cleaned = line.strip()
            if cleaned and cleaned not in education:
                education.append(cleaned)
    return education[:5]


def _estimate_experience_years(text: str) -> float | None:
    # Look for phrases like "5+ years of experience".
    match = re.search(
        r"(\d{1,2}(?:\.\d)?)\s*\+?\s*years?(?:\s+of)?\s+experience",
        text,
        re.IGNORECASE,
    )
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None
