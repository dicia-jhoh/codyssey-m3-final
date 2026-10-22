from uuid import UUID
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient

from app import main, notify
from app.sample import SAMPLE
from app.schema import Todo


def result(sample=False):
    return SAMPLE.model_copy(update={"sample": sample, "todos": [
        Todo(title="돈 내기", due="2026-10-31", amount=1200, how="앱"),
        Todo(title="서류 챙기기"),
        Todo(title="제출하기", due="2026-11-01"),
    ]})


@pytest.mark.parametrize("url,sample", [("", False), ("https://example.invalid", True)])
def test_unconfigured_or_sample_never_sends(monkeypatch, url, sample):
    monkeypatch.setenv("N8N_WEBHOOK_URL", url)
    post = Mock()
    monkeypatch.setattr(notify.httpx, "post", post)
    notify.notify_deadlines(result(sample))
    post.assert_not_called()


def test_only_deadlines_are_sent_with_expected_payload(monkeypatch):
    monkeypatch.setenv("N8N_WEBHOOK_URL", "https://example.invalid")
    post = Mock(return_value=Mock())
    monkeypatch.setattr(notify.httpx, "post", post)
    decoded = result()
    notify.notify_deadlines(decoded)
    assert post.call_count == 2
    ids = []
    for call, todo in zip(post.call_args_list, [decoded.todos[0], decoded.todos[2]]):
        payload = call.kwargs["json"]
        ids.append(UUID(payload.pop("todo_id")))
        assert payload == {**todo.model_dump(), "contact": ""}
        assert call.args == ("https://example.invalid",)
        assert call.kwargs["timeout"] == 5
    assert len(set(ids)) == 2


@pytest.mark.parametrize("error", [httpx.ConnectError("offline"), httpx.HTTPStatusError("bad", request=Mock(), response=Mock())])
def test_webhook_failure_preserves_decode_response(monkeypatch, caplog, error):
    monkeypatch.setenv("N8N_WEBHOOK_URL", "https://example.invalid")
    decoded = result()
    monkeypatch.setattr(main, "decode", lambda image: decoded)
    post = Mock(side_effect=[error, Mock()])
    monkeypatch.setattr(notify.httpx, "post", post)
    with TestClient(main.app) as client:
        response = client.post("/decode", files={"file": ("a.jpg", b"fake", "image/jpeg")})
    assert response.status_code == 200
    assert response.json() == decoded.model_dump()
    assert post.call_count == 2
    assert "n8n" in caplog.text


def test_http_error_response_is_logged(monkeypatch, caplog):
    monkeypatch.setenv("N8N_WEBHOOK_URL", "https://example.invalid")
    failed = Mock()
    failed.raise_for_status.side_effect = httpx.HTTPStatusError("bad", request=Mock(), response=Mock())
    monkeypatch.setattr(notify.httpx, "post", Mock(return_value=failed))
    notify.notify_deadlines(result())
    assert "HTTPStatusError" in caplog.text
