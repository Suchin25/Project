import json
import pytest
from unittest.mock import patch, MagicMock
import anthropic

from app import app


VALID_RESULT = {
    "summary": "This is a Series A term sheet with aggressive investor-friendly terms.",
    "key_terms": {
        "instrument": "Series A Preferred Stock",
        "valuation": "Pre-money $9M, Post-money $12M",
        "investment_amount": "$3,000,000",
        "liquidation_preference": "2x participating preferred",
        "anti_dilution": "Full ratchet",
        "board_composition": "2 investor seats, 1 founder seat",
        "pro_rata_rights": "Yes, for all investors",
        "vesting": "4-year, 2-year cliff",
    },
    "red_flags": [
        {
            "flag": "Full ratchet anti-dilution",
            "detail": "Extremely punitive in down rounds; pushes most dilution onto founders.",
            "severity": "high",
        }
    ],
    "score": {
        "overall": 38,
        "breakdown": {
            "founder_friendliness": 30,
            "valuation_fairness": 55,
            "control_terms": 25,
            "liquidity_terms": 35,
            "standard_terms": 45,
        },
        "verdict": "Heavily investor-friendly terms; several clauses warrant serious negotiation.",
    },
    "recommendations": [
        {
            "action": "Replace full ratchet with broad-based weighted average",
            "detail": "Full ratchet is rarely market standard. Most investors will accept broad-based.",
        }
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


def test_missing_termsheet_returns_400(client):
    resp = client.post("/analyze", json={})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_empty_termsheet_returns_400(client):
    resp = client.post("/analyze", json={"termsheet": "   "})
    assert resp.status_code == 400


def test_termsheet_too_long_returns_400(client):
    resp = client.post("/analyze", json={"termsheet": "x" * 20001})
    assert resp.status_code == 400
    assert "too long" in resp.get_json()["error"]


def test_valid_termsheet_returns_done_event(client):
    mock_stream = MockStream([json.dumps(VALID_RESULT)])

    with patch("app.client") as mock_client:
        mock_client.messages.stream.return_value = mock_stream
        resp = client.post("/analyze", json={"termsheet": "Series A term sheet content here"})

    assert resp.status_code == 200
    assert resp.content_type.startswith("text/event-stream")

    raw = resp.get_data(as_text=True)
    lines = [l for l in raw.split("\n") if l.startswith("data: ")]
    assert len(lines) == 1

    payload = json.loads(lines[0][6:])
    assert payload["status"] == "done"
    assert payload["result"]["score"]["overall"] == 38
    assert payload["result"]["key_terms"]["instrument"] == "Series A Preferred Stock"


def test_invalid_json_from_claude_returns_error(client):
    mock_stream = MockStream(["this is not valid json"])

    with patch("app.client") as mock_client:
        mock_client.messages.stream.return_value = mock_stream
        resp = client.post("/analyze", json={"termsheet": "Some term sheet"})

    raw = resp.get_data(as_text=True)
    lines = [l for l in raw.split("\n") if l.startswith("data: ")]
    payload = json.loads(lines[0][6:])
    assert payload["status"] == "error"


def test_anthropic_api_error_returns_error(client):
    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(
        side_effect=anthropic.APIError("API failure", request=MagicMock(), body=None)
    )
    mock_stream.__exit__ = MagicMock(return_value=False)

    with patch("app.client") as mock_client:
        mock_client.messages.stream.return_value = mock_stream
        resp = client.post("/analyze", json={"termsheet": "Some term sheet"})

    raw = resp.get_data(as_text=True)
    lines = [l for l in raw.split("\n") if l.startswith("data: ")]
    payload = json.loads(lines[0][6:])
    assert payload["status"] == "error"


def test_index_returns_200(client):
    resp = client.get("/")
    assert resp.status_code == 200
