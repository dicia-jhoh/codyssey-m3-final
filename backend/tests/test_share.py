import importlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import time

from app import share
from app.schema import Decoded
from app.share import create_share, get_share, share_expires_at


def _decoded() -> Decoded:
    return Decoded(doc_type="고지서", title="t", plain=[], marks=[], todos=[], basis=[])


def test_create_and_get_share_round_trip():
    share_id = create_share(_decoded())
    assert get_share(share_id) == _decoded()


def test_unknown_share_id_returns_none():
    assert get_share("없는-아이디") is None


def test_share_expires_at_is_ttl_after_creation():
    before = time.time()
    share_id = create_share(_decoded(), ttl_seconds=60)
    expires = share_expires_at(share_id)
    assert expires is not None and before + 60 <= expires <= time.time() + 60
    assert share_expires_at("없는-아이디") is None


def test_share_expiry_lookup_before_and_after_expiration(monkeypatch):
    monkeypatch.setattr(share.time, "time", lambda: 100.0)
    share_id = create_share(_decoded(), ttl_seconds=10)
    assert share_expires_at(share_id) == 110.0

    monkeypatch.setattr(share.time, "time", lambda: 110.0)
    assert share_expires_at(share_id) == 110.0

    monkeypatch.setattr(share.time, "time", lambda: 111.0)
    assert share_expires_at(share_id) is None


def test_expired_share_returns_none_and_is_removed():
    share_id = create_share(_decoded(), ttl_seconds=10)
    future = time.time() + 20  # TTL(10초)보다 더 지난 시점

    assert get_share(share_id, now=future) is None
    # 만료되면 그 자리에서 지워진다 — now 없이(진짜 현재 시각 기준) 다시 조회해도 없어야 함
    assert get_share(share_id) is None


def test_share_ids_are_unique():
    ids = {create_share(_decoded()) for _ in range(20)}
    assert len(ids) == 20


def test_oldest_share_dropped_when_full(monkeypatch):
    monkeypatch.setattr(share, "MAX_SHARES", 3)
    ids = [create_share(_decoded()) for _ in range(4)]
    assert get_share(ids[0]) is None
    assert all(get_share(i) is not None for i in ids[1:])


def test_share_survives_module_reload():
    share_id = create_share(_decoded())
    importlib.reload(share)
    assert share.get_share(share_id) == _decoded()


def test_expired_entries_are_cleaned_before_capacity_eviction(monkeypatch):
    monkeypatch.setattr(share, "MAX_SHARES", 2)
    monkeypatch.setattr(share.time, "time", lambda: 100)
    valid = create_share(_decoded())
    expired = create_share(_decoded(), ttl_seconds=-1)
    newest = create_share(_decoded())
    assert get_share(valid) == _decoded()
    assert get_share(expired) is None
    assert get_share(newest) == _decoded()


def test_only_decoded_json_is_stored(tmp_path):
    share_id = create_share(_decoded())
    with sqlite3.connect(tmp_path / "share.db") as db:
        body, expires, created = db.execute("SELECT body, expires_at, created_at FROM shares WHERE id = ?", (share_id,)).fetchone()
    assert body == _decoded().model_dump_json()
    assert expires - created == share.DEFAULT_TTL_SECONDS


def test_concurrent_share_requests():
    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(lambda _: create_share(_decoded()), range(20)))
        results = list(pool.map(get_share, ids))
    assert len(set(ids)) == 20
    assert results == [_decoded()] * 20


def test_share_db_is_owner_only(tmp_path):
    db = tmp_path / "share.db"
    db.touch(mode=0o644)
    create_share(_decoded())
    assert db.stat().st_mode & 0o777 == 0o600
