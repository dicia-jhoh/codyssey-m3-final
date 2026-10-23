"""기한 있는 실제 해독 결과만 n8n에 보낸다 — 담당: 이정관."""

import logging
import os
from uuid import uuid4

import httpx

from .schema import Decoded

log = logging.getLogger(__name__)


def notify_deadlines(decoded: Decoded) -> None:
    url = os.environ.get("N8N_WEBHOOK_URL", "").strip()
    if not url or decoded.sample:
        return
    for todo in decoded.todos:
        if not todo.due:
            continue
        try:
            response = httpx.post(
                url, json={"todo_id": str(uuid4()), **todo.model_dump(), "contact": ""}, timeout=5,
            )
            response.raise_for_status()
        except Exception as error:
            # 주소·연락처·문서 내용을 로그에 남기지 않는다. 다음 할 일은 계속 보낸다.
            log.warning("n8n 기한 알림 전송 실패: %s", type(error).__name__)
