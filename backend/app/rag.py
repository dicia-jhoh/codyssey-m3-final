"""근거 검색 — 담당: 김기훈.

할 일
1. 국가법령정보센터·정부24 안내를 모아 조문 하나 = 청크 하나로 Chroma 에 넣는다(조문 번호는 메타데이터).
2. 고지서 글자에서 「○○법 제○조」를 먼저 찾아 번호로 거르고, 그다음 문장 유사도로 고른다.
3. 찾은 근거는 schema.Basis 로 돌려준다. quote(원문 문장)가 비면 agent 가 그 풀이를 버린다.
"""

from .schema import Basis


def find_basis(text: str) -> list[Basis]:
    """고지서 글자에 맞는 근거 목록. 아직 구현 전이라 빈 목록을 낸다."""
    return []
