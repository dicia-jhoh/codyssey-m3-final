"""손주 모드 공유 — 사진 없이 해독 결과 JSON만 SQLite에 최대 30일 저장한다.

기본 DB는 저장소의 data/share.db다. SHARE_DB로 경로를 바꿀 수 있다.
재시작 후에도 링크를 읽을 수 있으며, 만료분과 1000개 초과분은 저장할 때 정리한다.
같은 링크를 연 사람들은 「다 했어요」 기록(할 일 키)을 함께 본다 — 공유가 지워지면 같이 지운다.
"""

from __future__ import annotations

import os
import secrets
import sqlite3
import threading
import time
from contextlib import closing
from pathlib import Path

from . import ROOT
from .schema import Decoded

DEFAULT_TTL_SECONDS = 30 * 24 * 60 * 60
MAX_SHARES = 1000
MAX_DONE_PER_SHARE = 50  # 고지서 한 장의 할 일은 몇 개다 — 이보다 많으면 해독 결과가 아니다
_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    path = Path(os.environ.get("SHARE_DB", "data/share.db"))
    if not path.is_absolute():
        path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, check_same_thread=False)
    # 해독 결과(금액·기한)가 담긴다 — 서버의 다른 계정이 못 읽게(OCR). 이미 있는 파일도 고친다
    os.chmod(path, 0o600)
    db.execute(
        "CREATE TABLE IF NOT EXISTS shares ("
        "id TEXT PRIMARY KEY, body TEXT NOT NULL, "
        "expires_at REAL NOT NULL, created_at REAL NOT NULL)"
    )
    # 저장·읽기마다 만료분을 지운다(expires_at < 지금) — 색인이 있어야 표를 다 훑지 않는다
    db.execute("CREATE INDEX IF NOT EXISTS shares_expires_at ON shares (expires_at)")
    db.execute(
        "CREATE TABLE IF NOT EXISTS share_done ("
        "share_id TEXT NOT NULL, todo_key TEXT NOT NULL, PRIMARY KEY (share_id, todo_key))"
    )
    return db


def _delete_expired(db: sqlite3.Connection, now: float) -> None:
    db.execute("DELETE FROM shares WHERE expires_at < ?", (now,))
    db.execute("DELETE FROM share_done WHERE share_id NOT IN (SELECT id FROM shares)")


def create_share(decoded: Decoded, *, ttl_seconds: float = DEFAULT_TTL_SECONDS) -> str:
    """해독 결과만 저장하고 공유 ID를 돌려준다."""
    share_id = secrets.token_urlsafe(8)
    now = time.time()
    with _lock, closing(_connect()) as db, db:
        _delete_expired(db, now)
        db.execute(
            "INSERT INTO shares VALUES (?, ?, ?, ?)",
            (share_id, decoded.model_dump_json(), now + ttl_seconds, now),
        )
        db.execute(
            "DELETE FROM shares WHERE id IN ("
            "SELECT id FROM shares ORDER BY created_at DESC, rowid DESC LIMIT -1 OFFSET ?)",
            (MAX_SHARES,),
        )
    return share_id


def get_share(share_id: str, *, now: float | None = None) -> Decoded | None:
    """없거나 만료된 공유는 None을 돌려주며 만료분은 지운다."""
    now = time.time() if now is None else now
    with _lock, closing(_connect()) as db, db:
        _delete_expired(db, now)
        row = db.execute("SELECT body FROM shares WHERE id = ?", (share_id,)).fetchone()
    return Decoded.model_validate_json(row[0]) if row else None


def share_expires_at(share_id: str) -> float | None:
    """공유가 사라지는 시각(유닉스 초). 없거나 이미 지났으면 None."""
    with _lock, closing(_connect()) as db:
        row = db.execute("SELECT expires_at FROM shares WHERE id = ?", (share_id,)).fetchone()
    if row is None or row[0] < time.time():
        return None
    return row[0]


def done_keys(share_id: str) -> list[str] | None:
    """그 공유에서 「다 했어요」를 누른 할 일 키. 없거나 만료된 공유는 None."""
    with _lock, closing(_connect()) as db, db:
        _delete_expired(db, time.time())
        if not _exists(db, share_id):
            return None
        rows = db.execute(
            "SELECT todo_key FROM share_done WHERE share_id = ? ORDER BY rowid", (share_id,)
        )
        return [key for (key,) in rows]


def mark_done(share_id: str, todo_key: str, *, done: bool) -> list[str] | None:
    """할 일 하나를 했다/안 했다로 적고 바뀐 목록을 돌려준다. 없거나 만료된 공유는 None.

    한 공유의 기록이 MAX_DONE_PER_SHARE 를 넘으면 ValueError — 인증 없는 공개 주소라
    아무나 키를 끝없이 쌓지 못하게 한다.
    """
    with _lock, closing(_connect()) as db, db:
        _delete_expired(db, time.time())
        if not _exists(db, share_id):
            return None
        if not done:
            db.execute(
                "DELETE FROM share_done WHERE share_id = ? AND todo_key = ?", (share_id, todo_key)
            )
        elif not _has_key(db, share_id, todo_key):  # 이미 적힌 키는 한도를 다시 세지 않는다
            count = db.execute(
                "SELECT COUNT(*) FROM share_done WHERE share_id = ?", (share_id,)
            ).fetchone()[0]
            if count >= MAX_DONE_PER_SHARE:
                raise ValueError("할 일 기록이 너무 많다")
            db.execute("INSERT INTO share_done VALUES (?, ?)", (share_id, todo_key))
        rows = db.execute(
            "SELECT todo_key FROM share_done WHERE share_id = ? ORDER BY rowid", (share_id,)
        )
        return [key for (key,) in rows]


def _has_key(db: sqlite3.Connection, share_id: str, todo_key: str) -> bool:
    row = db.execute(
        "SELECT 1 FROM share_done WHERE share_id = ? AND todo_key = ?", (share_id, todo_key)
    ).fetchone()
    return row is not None


def _exists(db: sqlite3.Connection, share_id: str) -> bool:
    return db.execute("SELECT 1 FROM shares WHERE id = ?", (share_id,)).fetchone() is not None
