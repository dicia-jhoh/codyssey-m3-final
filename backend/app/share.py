"""손주 모드 공유 — 해독 결과를 짧은 링크로 가족에게 보낸다(FR-07).

사진 원본은 절대 저장하지 않는다 — 이미 끝난 해독 결과(Decoded JSON)만 잠깐
메모리에 들고 있다가 기한이 지나면 지운다(AI 윤리: "손주 모드 링크도 해독 결과만
담고, 기한이 지나면 지운다" — docs/03-AI-설계.md).

단순화: "기한이 지나면"을 todos의 가장 이른 due로 정확히 계산하는 대신, 고정
TTL(기본 30일)로 둔다 — 서버 재시작하면 공유 링크도 전부 날아간다(인메모리라
당연함). 여러 서버/재시작 사이에도 유지해야 하면 SQLite 등으로 바꿀 자리.
"""

from __future__ import annotations

import secrets
import time

from .schema import Decoded

DEFAULT_TTL_SECONDS = 30 * 24 * 60 * 60  # 30일

_store: dict[str, tuple[Decoded, float]] = {}


def create_share(decoded: Decoded, *, ttl_seconds: float = DEFAULT_TTL_SECONDS) -> str:
    """해독 결과를 저장하고 공유 ID를 돌려준다."""
    share_id = secrets.token_urlsafe(8)
    _store[share_id] = (decoded, time.time() + ttl_seconds)
    return share_id


def get_share(share_id: str, *, now: float | None = None) -> Decoded | None:
    """공유 ID로 해독 결과를 찾는다. 없거나 기한이 지났으면 None(만료분은 그 자리에서 지움)."""
    entry = _store.get(share_id)
    if entry is None:
        return None
    decoded, expires_at = entry
    if (now if now is not None else time.time()) > expires_at:
        del _store[share_id]
        return None
    return decoded
