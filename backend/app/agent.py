"""해독 Agent — 담당: 오주현. 네 단계를 차례로 부른다(docs/03-AI-설계.md 「Agent 구조」).

① 판별 → ② 추출(extract.py, 황지영) → ③ 근거(rag.py, 김기훈) → ④ 답장 판단
키가 없거나 단계가 아직 빈 결과를 내면 샘플 모드로 돌아간다 — 화면이 깨지지 않게 하려는 것.
"""

import os

from . import extract, rag
from .redact import redact
from .sample import SAMPLE
from .schema import Decoded, Mark, Todo


def classify(text: str) -> str:
    """① 고지서 종류 판별. 지금은 낱말로만 고른다 — LLM 판별로 바꿀 자리."""
    for word, kind in [("납부", "고지서"), ("가정통신", "가정통신문"), ("신청", "신청서")]:
        if word in text:
            return kind
    return "안내문"


def _bbox_center_y(mark: Mark) -> float:
    return mark.bbox[1] + mark.bbox[3] / 2


def _nearest_by_position(target: Mark, candidates: list[Mark]) -> Mark | None:
    if not candidates:
        return None
    return min(candidates, key=lambda c: abs(_bbox_center_y(c) - _bbox_center_y(target)))


def _todos_from_marks(doc_type: str, marks: list[Mark]) -> list[Todo]:
    """money Mark 하나당 할 일 카드 하나를 만든다(②의 Mark에서 할 일 카드를 만드는 자리).

    Mark에는 "뭘 위한 돈인지" 같은 의미 정보가 없다(그건 근거/rag.py 쪽 몫) — 그래서
    제목은 지금은 문서 종류로만 만든다. rag 연동이 들어오면 더 구체적인 제목으로
    교체할 수 있는 자리. 기한은 세로 위치(bbox)가 가장 가까운 deadline Mark를 짝짓는다
    (같은 항목이면 보통 같은 줄 근처에 적혀 있다는 가정).
    """
    money_marks = [m for m in marks if m.kind == "money"]
    deadline_marks = [m for m in marks if m.kind == "deadline"]

    todos: list[Todo] = []
    for money in money_marks:
        deadline = _nearest_by_position(money, deadline_marks)
        try:
            amount = int(money.value)
        except ValueError:
            amount = None
        todos.append(
            Todo(
                title=f"{doc_type} 납부하기",
                due=deadline.value if deadline else None,
                amount=amount,
                how="은행 또는 앱 납부",
            )
        )
    return todos


def decode(image: bytes) -> Decoded:
    api_key = os.environ.get("LLM_API_KEY", "")
    if not api_key:
        return SAMPLE

    text, marks = extract.extract(image, api_key)
    if not text:
        return SAMPLE  # 추출이 아직 구현 전 — 샘플로 끝까지 돈다

    text = redact(text)  # 여기서부터는 가린 글자만 쓴다
    basis = [b for b in rag.find_basis(text) if b.quote]  # 근거 없는 풀이는 버린다
    doc_type = classify(text)
    return Decoded(
        doc_type=doc_type,
        title=text.splitlines()[0][:40],
        plain=[b.claim for b in basis][:3],
        marks=marks,
        todos=_todos_from_marks(doc_type, marks),
        basis=basis,
        reply_needed=doc_type == "신청서",
    )
