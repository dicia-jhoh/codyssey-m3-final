from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app import main
from app.schema import Decoded


@pytest.fixture
def decode(monkeypatch):
    fake = Mock(return_value=Decoded(
        doc_type="고지서", title="테스트", plain=[], marks=[], todos=[], basis=[], sample=True,
    ))
    monkeypatch.setattr(main, "decode", fake)
    return fake


def upload(client):
    return client.post("/decode", files={"file": ("a.jpg", b"fake", "image/jpeg")})


def test_eleventh_request_is_rejected_without_decoding(decode):
    with TestClient(main.app, client=("192.0.2.1", 1234)) as client:
        for _ in range(10):
            assert upload(client).status_code == 200
        response = upload(client)
        assert response.status_code == 429
        assert response.json() == {"detail": "잠시 뒤 다시 올려 주세요"}
        assert decode.call_count == 10
        assert client.get("/health").status_code == 200


def test_other_ip_has_its_own_limit(monkeypatch, decode):
    monkeypatch.setattr(main, "DECODE_PER_MINUTE", 1)
    with TestClient(main.app, client=("192.0.2.1", 1234)) as first:
        assert upload(first).status_code == 200
        assert upload(first).status_code == 429
    with TestClient(main.app, client=("192.0.2.2", 1234)) as second:
        assert upload(second).status_code == 200


def test_window_expires_and_old_ip_is_removed(monkeypatch, decode):
    now = [100.0]
    monkeypatch.setattr(main, "monotonic", lambda: now[0])
    monkeypatch.setattr(main, "DECODE_PER_MINUTE", 1)
    with TestClient(main.app, client=("192.0.2.1", 1234)) as first:
        assert upload(first).status_code == 200
        now[0] = 159.999
        assert upload(first).status_code == 429
        now[0] = 160.0
        with TestClient(main.app, client=("192.0.2.2", 1234)) as second:
            assert upload(second).status_code == 200
        assert "192.0.2.1" not in main._decode_requests
        assert upload(first).status_code == 200
