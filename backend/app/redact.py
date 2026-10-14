"""개인정보 가림 — LLM 에 보내기 전에 반드시 거친다(AI 윤리 요건).

사진은 extract 단계가 글자로 바꾼 뒤 이 함수를 지나야 RAG·답장 단계로 간다.
"""

import re

# 주민등록번호: 6자리-7자리. 뒷자리 첫 숫자는 1~4(내국인)·5~8(외국인)
_RRN = re.compile(r"\b(\d{6})[-\s]?([1-8])\d{6}\b")
# 계좌번호 후보: 숫자 묶음이 하이픈으로 3~4덩어리, 또는 숫자만 10~14자리
_ACCOUNT = re.compile(r"\b\d{2,6}(?:-\d{2,6}){2,3}\b|\b\d{10,14}\b")


def _hide_account(m: re.Match) -> str:
    # 날짜(2026-10-31, 숫자 8개)는 모양이 같아서 숫자 개수로 가른다 — 계좌는 10자리 이상이다
    digits = sum(c.isdigit() for c in m.group(0))
    return "[계좌번호 가림]" if digits >= 10 else m.group(0)


def redact(text: str) -> str:
    """주민번호는 앞 6자리와 성별 숫자만 남기고, 계좌번호는 통째로 가린다."""
    text = _RRN.sub(lambda m: f"{m.group(1)}-{m.group(2)}******", text)
    return _ACCOUNT.sub(_hide_account, text)
