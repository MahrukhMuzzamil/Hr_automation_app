from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from recruitment.services.matcher import MatchError, _parse_response, score_candidate


class DummyJob:
    title = "Backend Engineer"
    department = "Engineering"
    requirements = "Python, Django, PostgreSQL, 3+ years"
    description = ""


def test_parse_response_clamps_and_reads_justification():
    result = _parse_response('{"score": 140, "justification": "Great fit"}')
    assert result["score"] == 100.0
    assert result["justification"] == "Great fit"


def test_parse_response_rejects_bad_json():
    with pytest.raises(MatchError):
        _parse_response("not json")


def test_parse_response_requires_score():
    with pytest.raises(MatchError):
        _parse_response('{"justification": "no score"}')


@override_settings(OPENAI_API_KEY="")
def test_score_candidate_without_key_raises():
    with pytest.raises(MatchError):
        score_candidate(job=DummyJob(), parsed={"skills": ["python"]})


@override_settings(OPENAI_API_KEY="sk-test", OPENAI_MODEL="gpt-4o-mini")
@patch("openai.OpenAI")
def test_score_candidate_happy_path(mock_openai):
    message = MagicMock()
    message.content = '{"score": 82, "justification": "Strong Python match"}'
    completion = MagicMock()
    completion.choices = [MagicMock(message=message)]
    mock_openai.return_value.chat.completions.create.return_value = completion

    result = score_candidate(job=DummyJob(), parsed={"skills": ["python"]})
    assert result["score"] == 82.0
    assert "Python" in result["justification"]
