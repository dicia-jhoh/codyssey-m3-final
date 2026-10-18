import time

from app.schema import Decoded
from app.share import create_share, get_share


def _decoded() -> Decoded:
    return Decoded(doc_type="고지서", title="t", plain=[], marks=[], todos=[], basis=[])


def test_create_and_get_share_round_trip():
    share_id = create_share(_decoded())
    assert get_share(share_id) == _decoded()


def test_unknown_share_id_returns_none():
    assert get_share("없는-아이디") is None


def test_expired_share_returns_none_and_is_removed():
    share_id = create_share(_decoded(), ttl_seconds=10)
    future = time.time() + 20  # TTL(10초)보다 더 지난 시점

    assert get_share(share_id, now=future) is None
    # 만료되면 그 자리에서 지워진다 — now 없이(진짜 현재 시각 기준) 다시 조회해도 없어야 함
    assert get_share(share_id) is None


def test_share_ids_are_unique():
    ids = {create_share(_decoded()) for _ in range(20)}
    assert len(ids) == 20
