"""손주 모드 공유 — 사진 없이 해독 결과 JSON만 SQLite에 최대 30일 저장한다.

기본 DB는 저장소의 data/share.db다. SHARE_DB로 경로를 바꿀 수 있다.
재시작 후에도 링크를 읽을 수 있으며, 만료분과 1000개 초과분은 저장할 때 정리한다.
"""

from __future__ import annotations

from contextlib import closing
import os
from pathlib import Path
import secrets
import sqlite3
import threading
import time

from .schema import Decoded

DEFAULT_TTL_SECONDS = 30 * 24 * 60 * 60
MAX_SHARES = 1000
ROOT = Path(__file__).resolve().parents[2]
_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    path = Path(os.environ.get("SHARE_DB", "data/share.db"))
    if not path.is_absolute():
        path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, check_same_thread=False)
    # 해독 결과(금액·기한)가 담긴다 — 서버의 다른 계정이 못 읽게(OCR). 이미 있는 파일도 고친다
    os.chmod(path, 0o600)
    db.execute("CREATE TABLE IF NOT EXISTS shares (id TEXT PRIMARY KEY, body TEXT NOT NULL, expires_at REAL NOT NULL, created_at REAL NOT NULL)")
    return db


def create_share(decoded: Decoded, *, ttl_seconds: float = DEFAULT_TTL_SECONDS) -> str:
    """해독 결과만 저장하고 공유 ID를 돌려준다."""
    share_id = secrets.token_urlsafe(8)
    now = time.time()
    with _lock, closing(_connect()) as db, db:
        db.execute("DELETE FROM shares WHERE expires_at < ?", (now,))
        db.execute("INSERT INTO shares VALUES (?, ?, ?, ?)",
                   (share_id, decoded.model_dump_json(), now + ttl_seconds, now))
        db.execute("DELETE FROM shares WHERE id IN (SELECT id FROM shares ORDER BY created_at DESC, rowid DESC LIMIT -1 OFFSET ?)", (MAX_SHARES,))
    return share_id


def get_share(share_id: str, *, now: float | None = None) -> Decoded | None:
    """없거나 만료된 공유는 None을 돌려주며 만료분은 지운다."""
    now = time.time() if now is None else now
    with _lock, closing(_connect()) as db, db:
        db.execute("DELETE FROM shares WHERE expires_at < ?", (now,))
        row = db.execute("SELECT body FROM shares WHERE id = ?", (share_id,)).fetchone()
    return Decoded.model_validate_json(row[0]) if row else None


def share_expires_at(share_id: str) -> float | None:
    """공유가 사라지는 시각(유닉스 초). 없거나 이미 지났으면 None."""
    with _lock, closing(_connect()) as db:
        row = db.execute("SELECT expires_at FROM shares WHERE id = ?", (share_id,)).fetchone()
    if row is None or row[0] < time.time():
        return None
    return row[0]
