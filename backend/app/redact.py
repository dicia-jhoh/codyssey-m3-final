"""개인정보 가림 — LLM 에 보내기 전에 반드시 거친다(AI 윤리 요건).

사진은 extract 단계가 글자로 바꾼 뒤 이 함수를 지나야 RAG·답장 단계로 간다.
"""

import re

# 주민등록번호: 6자리-7자리. 뒷자리 첫 숫자는 1~4(내국인)·5~8(외국인)
_RRN = re.compile(r"\b(\d{6})[-\s]?([1-8])\d{6}\b")
# 계좌번호: 숫자 2~6개 묶음이 하이픈으로 3~4덩어리, 숫자만 10~14자리
_ACCOUNT = re.compile(r"\b\d{2,6}(?:-\d{2,6}){2,3}\b|\b\d{10,14}\b")


def redact(text: str) -> str:
    """주민번호는 앞 6자리와 성별 숫자만 남기고, 계좌번호는 통째로 가린다."""
    text = _RRN.sub(lambda m: f"{m.group(1)}-{m.group(2)}******", text)
    return _ACCOUNT.sub("[계좌번호 가림]", text)
