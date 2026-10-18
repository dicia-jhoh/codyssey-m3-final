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


_MAX_PAIR_DISTANCE = 0.15  # bbox 세로 비율 기준 — 이보다 멀면 같은 항목이 아니라고 본다


def _bbox_center_y(mark: Mark) -> float:
    return mark.bbox[1] + mark.bbox[3] / 2


def _nearest_within_distance(
    target: Mark, candidates: list[Mark], *, max_distance: float
) -> tuple[int, Mark] | None:
    """세로 위치가 가장 가까운 (인덱스, Mark)를 돌려준다.

    max_distance보다 멀면 아예 None — 틀린 짝짓기(예: 금액 옆이 아니라 문서 맨 아래
    「이의신청 기한」이 붙는 것)가 기한 없음보다 위험하다(D-day 알림이 틀어짐).
    """
    if not candidates:
        return None
    nearest_idx = min(
        range(len(candidates)),
        key=lambda i: abs(_bbox_center_y(candidates[i]) - _bbox_center_y(target)),
    )
    if abs(_bbox_center_y(candidates[nearest_idx]) - _bbox_center_y(target)) > max_distance:
        return None
    return nearest_idx, candidates[nearest_idx]


def _title_for(doc_type: str, *, has_money: bool) -> str:
    """카드 종류(돈이 있는지)로 제목을 고른다 — doc_type만으로 고르면 「안내문 납부하기」
    처럼 안 맞는 조합이 나올 수 있다."""
    if has_money:
        return f"{doc_type} 금액 내기"
    if doc_type == "신청서":
        return "신청하기"
    return f"{doc_type} 제출하기"


def _todos_from_marks(doc_type: str, marks: list[Mark]) -> list[Todo]:
    """Mark에서 할 일 카드를 만든다(②의 Mark에서 할 일 카드를 만드는 자리).

    money Mark 하나당 카드 하나, 세로 위치가 가장 가깝고 _MAX_PAIR_DISTANCE 이내인
    deadline Mark를 기한으로 짝짓는다. 어떤 money와도 짝지어지지 않은 deadline Mark도
    카드 한 장으로 만든다(amount=None) — 신청서·가정통신문처럼 돈 없이 기한만 있는
    문서도 할 일이다(FR-05는 납부만이 아니라 「할 일」 전체를 다룬다).

    Mark에는 "뭘 위한 돈/기한인지" 같은 의미 정보가 없다(그건 근거/rag.py 쪽 몫) —
    제목은 지금은 문서 종류 + 카드 종류로만 만든다. rag 연동이 들어오면 더 구체적인
    제목으로 교체할 수 있는 자리.
    """
    money_marks = [m for m in marks if m.kind == "money"]
    deadline_marks = [m for m in marks if m.kind == "deadline"]

    todos: list[Todo] = []
    paired = [False] * len(deadline_marks)

    for money in money_marks:
        hit = _nearest_within_distance(money, deadline_marks, max_distance=_MAX_PAIR_DISTANCE)
        deadline_idx, deadline = hit if hit else (None, None)
        if deadline_idx is not None:
            paired[deadline_idx] = True

        try:
            amount = int(money.value)
        except ValueError:
            amount = None

        todos.append(
            Todo(
                title=_title_for(doc_type, has_money=True),
                due=deadline.value if deadline else None,
                amount=amount,
                how="은행 또는 앱 납부",
            )
        )

    for idx, deadline in enumerate(deadline_marks):
        if paired[idx]:
            continue
        todos.append(
            Todo(
                title=_title_for(doc_type, has_money=False),
                due=deadline.value,
                amount=None,
                how="",
            )
        )

    return todos


def decode(image: bytes) -> Decoded:
    api_key = os.environ.get("LLM_API_KEY", "")
    if not api_key:
        return SAMPLE

    text, marks = extract.extract(image, api_key)
    if not text:
        return SAMPLE  # 추출 실패(원인은 extract 가 로그에 남김) — 샘플 배너를 띄워 끝까지 돈다

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
