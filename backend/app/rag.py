"""근거 검색 — 담당: 김기훈.

할 일
1. 국가법령정보센터·정부24 안내를 모아 조문 하나 = 청크 하나로 Chroma 에 넣는다(조문 번호는
   메타데이터) — `add_article()`로 넣는다. 지금은 배관(이 파일)만 있고 실제 법령 데이터는
   비어 있다.
2. 고지서 글자에서 「○○법 제○조」를 먼저 찾아 번호로 거르고, 그다음 문장 유사도로 고른다.
   지금은 조문 번호 인용이 있을 때만 찾는다 — 유사도 검색(인용이 없어도 비슷한 내용을
   찾는 것)은 진짜 임베딩이 필요해서 아직 배관이 없다(아래 `add_article()` 참고).
3. 찾은 근거는 schema.Basis 로 돌려준다. quote(원문 문장)가 비면 agent 가 그 풀이를 버린다.
"""

from __future__ import annotations

import re
from pathlib import Path

import chromadb

from .schema import Basis

_CHROMA_DIR = Path(__file__).resolve().parents[2] / "data" / "legal" / "chroma"
_COLLECTION_NAME = "legal_articles"

# "국민건강보험법 제80조", "지방세법 제15조" 같은 인용을 찾는다.
_CITATION_RE = re.compile(r"([가-힣]+법)\s*제\s*(\d+)\s*조")

_client: chromadb.ClientAPI | None = None


def _collection():
    """지연 초기화한 Chroma 컬렉션 — `data/legal/chroma/`에 영속화(.gitignore 대상)."""
    global _client
    if _client is None:
        _CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
    return _client.get_or_create_collection(_COLLECTION_NAME)


def add_article(*, law_name: str, article_no: str, quote: str, claim: str) -> None:
    """법령 조문 하나를 청크 하나로 넣는다 — 실제 수집 데이터를 넣는 진입점.

    quote: 조문 원문 그대로. claim: 그 조문을 쉬운 말로 풀어쓴 한 줄(Basis.claim에 그대로
    들어감) — 여기서 자동으로 만들어내지 않는다. 지어낸 풀이를 근거랍시고 내보내면 이
    서비스의 핵심 원칙("근거 없는 문장은 안 낸다")을 어기게 된다.

    embeddings는 지금 더미값([0.0])을 쓴다 — Chroma 기본 임베딩 함수는 첫 호출 때 ~80MB
    모델을 내려받는데, 이게 느린 네트워크에서 분 단위로 걸려서 배관 단계에서는 피했다.
    진짜 문장 유사도 검색을 붙일 때 이 함수 내부만 바꾸면 되고, 시그니처는 그대로 둬도 된다.
    """
    collection = _collection()
    collection.upsert(
        ids=[f"{law_name}-{article_no}"],
        documents=[quote],
        embeddings=[[0.0]],
        metadatas=[{"law_name": law_name, "article_no": article_no, "claim": claim}],
    )


def _citations(text: str) -> list[tuple[str, str]]:
    """고지서 글자에서 "○○법 제○조" 패턴을 전부 뽑는다."""
    return _CITATION_RE.findall(text)


def find_basis(text: str) -> list[Basis]:
    """고지서 글자에 맞는 근거 목록을 찾는다.

    조문 번호 인용이 본문에 있을 때만 찾는다(유사도 검색은 아직 없음 — 모듈 docstring
    참고). 컬렉션이 비어 있으면(아직 실제 법령 데이터 미수집) 빈 목록을 낸다 — 근거
    없는 문장을 지어내지 않는다는 원칙 그대로.
    """
    collection = _collection()
    if collection.count() == 0:
        return []

    results: list[Basis] = []
    for law_name, article_no in _citations(text):
        hit = collection.get(
            where={"$and": [{"law_name": {"$eq": law_name}}, {"article_no": {"$eq": article_no}}]}
        )
        for doc, meta in zip(hit["documents"], hit["metadatas"]):
            results.append(Basis(claim=meta["claim"], quote=doc, law=f"{law_name} 제{article_no}조"))

    return results
