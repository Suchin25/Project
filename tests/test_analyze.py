import json
import pytest
from unittest.mock import patch, MagicMock
import anthropic

from app import app


VALID_RESULT = {
    "summary": "A marketplace connecting local farmers with restaurants.",
    "market": {
        "size": "$50B US food distribution market",
        "competitors": ["Sysco", "US Foods", "Local Harvest"],
        "positioning": "Cuts out distributors with real-time surplus matching",
        "timing": "Post-COVID supply chain disruptions make this timely",
    },
    "red_flags": [
        {"flag": "Cold start problem", "detail": "Needs both farmers and restaurants simultaneously."}
    ],
    "score": {
        "overall": 68,
        "breakdown": {
            "market_opportunity": 80,
            "feasibility": 60,
            "differentiation": 65,
            "timing": 72,
            "team_fit": 65,
        },
        "verdict": "Promising concept with a real chicken-and-egg challenge to solve.",
    },
    "next_steps": [
        {"step": "Pilot in one city", "detail": "Recruit 10 farmers and 20 restaurants in a single market."}
    ],
}


class MockStream:
    def __init__(self, texts):
        self.text_stream = iter(texts)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["RATELIMIT_ENABLED"] = False
    with app.test_client() as c:
        yield c


def test_missing_idea_returns_400(client):
    resp = client.post("/analyze", json={})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_empty_idea_returns_400(client):
    resp = client.post("/analyze", json={"idea": "   "})
    assert resp.status_code == 400


def test_idea_too_long_returns_400(client):
    resp = client.post("/analyze", json={"idea": "x" * 5001})
    assert resp.status_code == 400
    assert "too long" in resp.get_json()["error"]


def test_valid_idea_returns_done_event(client):
    mock_stream = MockStream([json.dumps(VALID_RESULT)])

    with patch("app.client") as mock_client:
        mock_client.messages.stream.return_value = mock_stream
        resp = client.post("/analyze", json={"idea": "Farmers marketplace for restaurants"})

    assert resp.status_code == 200
    assert resp.content_type.startswith("text/event-stream")

    raw = resp.get_data(as_text=True)
    lines = [l for l in raw.split("\n") if l.startswith("data: ")]
    assert len(lines) == 1

    payload = json.loads(lines[0][6:])
    assert payload["status"] == "done"
    assert payload["result"]["score"]["overall"] == 68


def test_invalid_json_from_claude_returns_error(client):
    mock_stream = MockStream(["this is not valid json"])

    with patch("app.client") as mock_client:
        mock_client.messages.stream.return_value = mock_stream
        resp = client.post("/analyze", json={"idea": "Some idea"})

    raw = resp.get_data(as_text=True)
    lines = [l for l in raw.split("\n") if l.startswith("data: ")]
    payload = json.loads(lines[0][6:])
    assert payload["status"] == "error"


def test_anthropic_api_error_returns_error(client):
    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(side_effect=anthropic.APIError("API failure", request=MagicMock(), body=None))
    mock_stream.__exit__ = MagicMock(return_value=False)

    with patch("app.client") as mock_client:
        mock_client.messages.stream.return_value = mock_stream
        resp = client.post("/analyze", json={"idea": "Some idea"})

    raw = resp.get_data(as_text=True)
    lines = [l for l in raw.split("\n") if l.startswith("data: ")]
    payload = json.loads(lines[0][6:])
    assert payload["status"] == "error"


def test_index_returns_200(client):
    resp = client.get("/")
    assert resp.status_code == 200
