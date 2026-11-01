import pytest


@pytest.fixture(autouse=True)
def isolate_share_database(monkeypatch, tmp_path):
    monkeypatch.setenv("SHARE_DB", str(tmp_path / "share.db"))


@pytest.fixture(autouse=True)
def isolate_decode_rate_limit(monkeypatch):
    from app import main

    monkeypatch.setattr(main, "_decode_requests", {})


@pytest.fixture(autouse=True)
def isolate_chroma(monkeypatch, tmp_path):
    """테스트마다 빈 Chroma 폴더를 쓴다 — 실제 data/legal/chroma/ 를 건드리지 않는다."""
    from app import rag

    monkeypatch.setattr(rag, "_CHROMA_DIR", tmp_path / "chroma")
    monkeypatch.setattr(rag, "_client", None)
