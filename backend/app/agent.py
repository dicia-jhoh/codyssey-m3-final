"""해독 Agent — 담당: 오주현. 네 단계를 차례로 부른다(docs/03-AI-설계.md 「Agent 구조」).

① 판별 → ② 추출(extract.py, 황지영) → ③ 근거(rag.py, 김기훈) → ④ 답장 판단
키가 없거나 단계가 아직 빈 결과를 내면 샘플 모드로 돌아간다 — 화면이 깨지지 않게 하려는 것.
"""

import os

from . import extract, rag
from .redact import redact
from .sample import SAMPLE
from .schema import Decoded


def classify(text: str) -> str:
    """① 고지서 종류 판별. 지금은 낱말로만 고른다 — LLM 판별로 바꿀 자리."""
    for word, kind in [("납부", "고지서"), ("가정통신", "가정통신문"), ("신청", "신청서")]:
        if word in text:
            return kind
    return "안내문"


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
        todos=[],  # ② 의 Mark 에서 할 일 카드를 만드는 자리
        basis=basis,
        reply_needed=doc_type == "신청서",
    )
