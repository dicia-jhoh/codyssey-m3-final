import importlib
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import pytest

from app import share
from app.schema import Decoded, Todo
from app.share import create_share, get_share, share_expires_at


def _decoded() -> Decoded:
    return Decoded(doc_type="고지서", title="t", plain=[], marks=[], todos=[], basis=[])


def _with_todos(*titles: str) -> Decoded:
    todos = [Todo(title=t, due="2099-01-01", amount=1000) for t in titles]
    return _decoded().model_copy(update={"todos": todos})


def _key(decoded: Decoded, i: int) -> str:
    return share.key_of(decoded, decoded.todos[i])


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
        body, expires, created = db.execute(
            "SELECT body, expires_at, created_at FROM shares WHERE id = ?", (share_id,)
        ).fetchone()
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


def test_done_keys_are_shared_between_everyone_who_opens_the_link():
    decoded = _with_todos("돈 내기")
    share_id = create_share(decoded)
    card = _key(decoded, 0)
    assert card == '["t","돈 내기","2099-01-01",1000]'  # 화면 JSON.stringify 와 같은 모양
    assert share.done_keys(share_id) == []
    assert share.mark_done(share_id, card, done=True) == [card]
    assert share.mark_done(share_id, card, done=True) == [card]  # 두 번 눌러도 하나
    assert share.done_keys(share_id) == [card]
    assert share.mark_done(share_id, card, done=False) == []


def test_done_keys_of_unknown_or_expired_share_is_none(monkeypatch):
    assert share.done_keys("없는-아이디") is None
    assert share.mark_done("없는-아이디", "카드1", done=True) is None
    monkeypatch.setattr(share.time, "time", lambda: 100.0)
    decoded = _with_todos("돈 내기")
    share_id = create_share(decoded, ttl_seconds=10)
    share.mark_done(share_id, _key(decoded, 0), done=True)
    monkeypatch.setattr(share.time, "time", lambda: 111.0)
    assert share.done_keys(share_id) is None


def test_key_that_is_not_one_of_the_shared_todos_is_rejected():
    share_id = create_share(_with_todos("돈 내기"))
    with pytest.raises(KeyError):
        share.mark_done(share_id, "아무 키", done=True)


def test_done_keys_per_share_are_capped(monkeypatch):
    monkeypatch.setattr(share, "MAX_DONE_PER_SHARE", 2)
    decoded = _with_todos("a", "b", "c")
    share_id = create_share(decoded)
    share.mark_done(share_id, _key(decoded, 0), done=True)
    share.mark_done(share_id, _key(decoded, 1), done=True)
    with pytest.raises(ValueError):
        share.mark_done(share_id, _key(decoded, 2), done=True)


def test_done_key_already_recorded_is_accepted_at_the_cap(monkeypatch):
    """한도가 찬 공유에 이미 적힌 키를 다시 보내도 413 이 아니다(공유할 때 다시 보낸다)."""
    monkeypatch.setattr(share, "MAX_DONE_PER_SHARE", 1)
    decoded = _with_todos("a")
    share_id = create_share(decoded)
    share.mark_done(share_id, _key(decoded, 0), done=True)
    assert share.mark_done(share_id, _key(decoded, 0), done=True) == [_key(decoded, 0)]


def test_evicted_share_takes_its_done_keys_with_it(monkeypatch):
    monkeypatch.setattr(share, "MAX_SHARES", 1)
    decoded = _with_todos("a")
    first = create_share(decoded)
    share.mark_done(first, _key(decoded, 0), done=True)
    create_share(decoded)  # 한도 1 — 첫 공유가 밀려난다
    with closing(share._connect()) as db:
        assert db.execute("SELECT COUNT(*) FROM share_done").fetchone()[0] == 0
