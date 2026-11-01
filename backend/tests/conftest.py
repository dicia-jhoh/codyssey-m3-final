import pytest


@pytest.fixture(autouse=True)
def isolate_share_database(monkeypatch, tmp_path):
    monkeypatch.setenv("SHARE_DB", str(tmp_path / "share.db"))


@pytest.fixture(autouse=True)
def isolate_decode_rate_limit(monkeypatch):
    from app import main

    monkeypatch.setattr(main, "_decode_requests", {})
