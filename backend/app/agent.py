"""해독 Agent — 담당: 오주현. 다섯 단계를 차례로 부른다(docs/03-AI-설계.md 「Agent 구조」).

① 추출(extract.py, 황지영) → ② 가림(redact.py, 이정관) → ③ 근거(rag.py, 김기훈)
→ ④ 판별 → ⑤ 할 일. 기한 알림은 main.py 가 응답 뒤에 따로 보낸다(notify.py).
키가 없거나 추출이 빈 결과를 내면 샘플 모드로 돌아간다 — 화면이 깨지지 않게 하려는 것.
"""

import os

from . import extract, rag
from .redact import redact
from .sample import SAMPLE
from .schema import Decoded, Mark, Todo

_MAX_PAIR_DISTANCE = 0.15  # bbox 세로 비율 기준 — 이보다 멀면 같은 항목이 아니라고 본다
TITLE_MAX_CHARS = 40  # 카드 제목 = 본문 첫 줄을 이만큼 자른다
PLAIN_MAX_LINES = 3  # 쉬운 말 풀이는 근거 세 개까지 — 어르신 화면 한 눈
PAY_HOW = "은행 또는 앱 납부"


def classify(text: str) -> str:
    """① 고지서 종류 판별. 지금은 낱말로만 고른다 — LLM 판별로 바꿀 자리."""
    for word, kind in [("납부", "고지서"), ("가정통신", "가정통신문"), ("신청", "신청서")]:
        if word in text:
            return kind
    return "안내문"


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
        return f"{doc_type} 돈 내기"
    if doc_type == "신청서":
        return "신청서 내기"
    return f"{doc_type} 내기"


def _how(*parts: str) -> str:
    """how 필드 조각을 화면 표기(" · ")와 같은 구분자로 잇는다 — 빈 조각은 버린다."""
    return " · ".join(p for p in parts if p)


def _preparation_note(marks: list[Mark]) -> str:
    """document Mark(챙겨야 할 서류)를 짧은 준비물 문구로 합친다.

    document Mark에는 "어느 할 일을 위한 서류인지" 정보가 없어(money/deadline처럼
    bbox로 짝지을 기준이 없다 — 서류 안내는 보통 문서 전체에 한 번 적힌다), 모든
    할 일 카드에 공통 준비물로 붙인다.
    """
    docs = [m.text for m in marks if m.kind == "document"]
    return f"{', '.join(docs)} 챙기기" if docs else ""


def _todos_from_marks(doc_type: str, marks: list[Mark]) -> list[Todo]:
    """Mark에서 할 일 카드를 만든다(②의 Mark에서 할 일 카드를 만드는 자리).

    money Mark 하나당 카드 하나, 세로 위치가 가장 가깝고 _MAX_PAIR_DISTANCE 이내인
    deadline Mark를 기한으로 짝짓는다. 어떤 money와도 짝지어지지 않은 deadline Mark도
    카드 한 장으로 만든다(amount=None) — 신청서·가정통신문처럼 돈 없이 기한만 있는
    문서도 할 일이다(FR-05는 납부만이 아니라 「할 일」 전체를 다룬다).

    document Mark는 how 필드의 준비물 문구로 쓴다(_preparation_note) — 이슈 #20 4번.

    Mark에는 "뭘 위한 돈/기한인지" 같은 의미 정보가 없다(그건 근거/rag.py 쪽 몫) —
    제목은 지금은 문서 종류 + 카드 종류로만 만든다. rag 연동이 들어오면 더 구체적인
    제목으로 교체할 수 있는 자리.
    """
    deadline_marks = [m for m in marks if m.kind == "deadline"]
    prep = _preparation_note(marks)
    paired: set[int] = set()
    todos = [
        _money_todo(doc_type, money, deadline_marks, paired, prep)
        for money in marks
        if money.kind == "money"
    ]
    todos += [
        Todo(title=_title_for(doc_type, has_money=False), due=d.value, amount=None, how=_how(prep))
        for i, d in enumerate(deadline_marks)
        if i not in paired
    ]
    return todos


def _money_todo(
    doc_type: str, money: Mark, deadline_marks: list[Mark], paired: set[int], prep: str
) -> Todo:
    """돈 하나 = 카드 하나. 가장 가까운 기한을 짝짓고, 짝지은 기한 번호를 paired 에 남긴다."""
    hit = _nearest_within_distance(money, deadline_marks, max_distance=_MAX_PAIR_DISTANCE)
    if hit:
        paired.add(hit[0])
    return Todo(
        title=_title_for(doc_type, has_money=True),
        due=hit[1].value if hit else None,
        amount=_amount_of(money),
        how=_how(PAY_HOW, prep),
    )


def _amount_of(money: Mark) -> int | None:
    # extract 를 거친 값은 늘 숫자지만, 샘플·손으로 만든 Mark 는 아닐 수 있다
    try:
        return int(money.value)
    except ValueError:
        return None


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
        title=text.splitlines()[0][:TITLE_MAX_CHARS],
        plain=[b.claim for b in basis][:PLAIN_MAX_LINES],
        marks=marks,
        todos=_todos_from_marks(doc_type, marks),
        basis=basis,
        reply_needed=doc_type == "신청서",
    )
