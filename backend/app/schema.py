"""해독 결과의 모양 — 담당: 오주현.

화면(web/)과 n8n 은 이 모양만 믿는다. 필드를 바꾸면 docs/02-기능명세.md 의 「데이터 모델」 표도 같이 고친다.
"""

from typing import Literal

from pydantic import BaseModel

MarkKind = Literal["money", "deadline", "document"]  # 빨강 · 파랑 · 초록


class Mark(BaseModel):
    """원본 사진 위 표시 하나."""

    kind: MarkKind
    text: str  # 원문 글자 그대로, 예: "48,200원"
    value: str  # 다루기 쉬운 값, 예: "48200", "2026-10-31"
    bbox: list[float]  # 사진 크기 대비 비율 [x, y, w, h], 0~1


class Todo(BaseModel):
    """할 일 카드 한 장."""

    title: str  # 예: "건강보험료 내기"
    due: str | None = None  # "YYYY-MM-DD"
    amount: int | None = None  # 원
    how: str = ""  # 예: "은행 또는 앱 납부"


class Basis(BaseModel):
    """쉬운 말 풀이 한 줄과 그 근거. quote 가 비어 있으면 화면에 내지 않는다."""

    claim: str  # 쉬운 말 풀이
    quote: str  # 원문 문장
    law: str = ""  # 예: "국민건강보험법 제80조"


class Decoded(BaseModel):
    """POST /decode 응답 전체."""

    doc_type: Literal["고지서", "가정통신문", "안내문", "신청서", "기타"]
    title: str
    plain: list[str]  # 쉬운 말 요약, 3줄 이내
    marks: list[Mark]
    todos: list[Todo]
    basis: list[Basis]
    reply_needed: bool = False
    reply_draft: str = ""
    sample: bool = False  # True 면 샘플 모드 — 화면이 배너를 띄운다
    ai_notice: str = "AI 풀이 — 원문을 함께 확인하세요"
