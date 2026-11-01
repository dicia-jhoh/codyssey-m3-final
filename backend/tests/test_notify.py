from datetime import date
from unittest.mock import Mock
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient

from app import main, notify
from app.sample import SAMPLE
from app.schema import Todo


def result(sample=False):
    return SAMPLE.model_copy(
        update={
            "sample": sample,
            "todos": [
                Todo(title="돈 내기", due="2099-10-31", amount=1200, how="앱"),
                Todo(title="서류 챙기기"),
                Todo(title="제출하기", due="2099-11-01"),
            ],
        }
    )


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
    for call, todo in zip(post.call_args_list, [decoded.todos[0], decoded.todos[2]], strict=True):
        payload = call.kwargs["json"]
        ids.append(UUID(payload.pop("todo_id")))
        assert payload == {
            "title": todo.title,
            "due": todo.due,
            "contact": "",
        }  # 금액·방법은 안 보낸다
        assert call.args == ("https://example.invalid",)
        assert call.kwargs["timeout"] == 5
    assert len(set(ids)) == 2


@pytest.mark.parametrize(
    "error",
    [httpx.ConnectError("offline"), httpx.HTTPStatusError("bad", request=Mock(), response=Mock())],
)
def test_webhook_failure_preserves_decode_response(monkeypatch, caplog, error):
    monkeypatch.setenv("N8N_WEBHOOK_URL", "https://example.invalid")
    decoded = result()
    monkeypatch.setattr(main, "decode", lambda image: decoded)
    post = Mock(side_effect=[error, Mock()])
    monkeypatch.setattr(notify.httpx, "post", post)
    with TestClient(main.app) as client:
        response = client.post("/decode", files={"file": ("a.jpg", b"fake", "image/jpeg")})
    assert response.status_code == 200
    body = response.json()
    assert body.pop("alerts") and body == decoded.model_dump(exclude={"alerts"})
    assert post.call_count == 2
    assert "n8n" in caplog.text


def test_http_error_response_is_logged(monkeypatch, caplog):
    monkeypatch.setenv("N8N_WEBHOOK_URL", "https://example.invalid")
    failed = Mock()
    failed.raise_for_status.side_effect = httpx.HTTPStatusError(
        "bad", request=Mock(), response=Mock()
    )
    monkeypatch.setattr(notify.httpx, "post", Mock(return_value=failed))
    notify.notify_deadlines(result())
    assert "HTTPStatusError" in caplog.text


def test_alerts_three_days_before_and_on_the_day():
    decoded = result()
    alerts = notify.kakao_alerts(decoded, today=date(2099, 10, 1))
    assert [(a.send_on, a.when) for a in alerts] == [
        ("2099-10-28", "사흘 전"),
        ("2099-10-29", "사흘 전"),
        ("2099-10-31", "당일"),
        ("2099-11-01", "당일"),
    ]
    assert alerts[0].message == "[또박또박] 돈 내기 — 1,200원, 10월 31일까지예요. 사흘 남았어요."
    assert alerts[3].message == "[또박또박] 제출하기 — 11월 1일까지예요. 오늘까지예요."


def test_no_alert_for_a_past_deadline_and_only_today_when_too_close():
    alerts = notify.kakao_alerts(result(), today=date(2099, 10, 31))
    assert [(a.send_on, a.when) for a in alerts] == [("2099-10-31", "당일"), ("2099-11-01", "당일")]
    assert notify.kakao_alerts(result(), today=date(2099, 11, 2)) == []


def test_past_deadline_is_not_sent_to_n8n(monkeypatch):
    monkeypatch.setenv("N8N_WEBHOOK_URL", "https://example.invalid")
    post = Mock(return_value=Mock())
    monkeypatch.setattr(notify.httpx, "post", post)
    past = result().model_copy(update={"todos": [Todo(title="지난 일", due="2000-01-01")]})
    notify.notify_deadlines(past)
    post.assert_not_called()


def test_today_is_korean_date_not_server_date(monkeypatch):
    """서버(UTC)가 11-01 23시면 한국은 11-02 다 — 11-01 기한의 「당일」 알림은 없다."""
    from datetime import UTC
    from datetime import datetime as real_datetime

    class Clock(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime(2099, 11, 1, 23, 0, tzinfo=UTC).astimezone(tz)

    monkeypatch.setattr(notify, "datetime", Clock)
    late = result().model_copy(update={"todos": [Todo(title="돈 내기", due="2099-11-01")]})
    assert notify.kakao_alerts(late) == []
