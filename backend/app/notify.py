"""기한 알림 — 담당: 이정관.

할 일마다 기한 사흘 전·당일 오전 9시에 보낼 카카오톡 알림을 만든다. 카카오톡은 연결하지 않은
가상 발송이다 — 화면이 말풍선으로 미리 보여 주고, 서버에 N8N_WEBHOOK_URL 이 있으면 같은 일정을
n8n 에 넘긴다(실제 발송 노드는 비활성). 이미 지난 기한은 알리지 않는다.
"""

import logging
import os
from datetime import date, timedelta
from uuid import uuid4

import httpx

from .schema import Alert, Decoded, Todo

log = logging.getLogger(__name__)

ALERT_HOUR = 9  # 알림 시각(오전 9시) — 어르신이 아침에 확인하기 쉬운 때
DAYS_BEFORE = 3
_WEBHOOK_TIMEOUT_SECONDS = 5


def kakao_alerts(decoded: Decoded, *, today: date | None = None) -> list[Alert]:
    """할 일마다 사흘 전·당일 알림. 지난 날짜의 알림은 만들지 않는다(샘플도 같은 규칙)."""
    today = today or date.today()
    alerts: list[Alert] = []
    for todo in decoded.todos:
        due = _due_date(todo)
        if due is None or due < today:
            continue
        early = due - timedelta(days=DAYS_BEFORE)
        if early >= today:
            alerts.append(
                Alert(
                    send_on=early.isoformat(),
                    when="사흘 전",
                    message=_message(todo, due, "사흘 남았어요"),
                )
            )
        alerts.append(
            Alert(send_on=due.isoformat(), when="당일", message=_message(todo, due, "오늘까지예요"))
        )
    return sorted(alerts, key=lambda a: a.send_on)


def notify_deadlines(decoded: Decoded) -> None:
    """서버에 N8N_WEBHOOK_URL 이 있으면 실제 해독의 알림 일정을 n8n 에 넘긴다."""
    url = os.environ.get("N8N_WEBHOOK_URL", "").strip()
    if not url or decoded.sample:
        return
    for todo in decoded.todos:
        due = _due_date(todo)
        if due is None or due < date.today():
            continue
        try:
            # 알림 문구에 쓰는 것만 보낸다 — 금액·납부 방법은 n8n 이 안 쓰는데 밖으로 나간다(OCR)
            payload = {"todo_id": str(uuid4()), "title": todo.title, "due": todo.due, "contact": ""}
            response = httpx.post(url, json=payload, timeout=_WEBHOOK_TIMEOUT_SECONDS)
            response.raise_for_status()
        except Exception as error:
            # 주소·연락처·문서 내용을 로그에 남기지 않는다. 다음 할 일은 계속 보낸다.
            log.warning("n8n 기한 알림 전송 실패: %s", type(error).__name__)


def _due_date(todo: Todo) -> date | None:
    try:
        return date.fromisoformat(todo.due) if todo.due else None
    except ValueError:
        return None


def _message(todo: Todo, due: date, left: str) -> str:
    money = f" {todo.amount:,}원," if todo.amount is not None else ""
    return f"[또박또박] {todo.title} —{money} {due.month}월 {due.day}일까지예요. {left}."
