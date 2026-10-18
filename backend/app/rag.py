"""근거 검색 — 담당: 김기훈.

할 일
1. 국가법령정보센터·정부24 안내를 모아 조문 하나 = 청크 하나로 Chroma 에 넣는다(조문 번호는
   메타데이터) — `add_article()`로 넣는다. 원본은 data/legal/articles.jsonl, 적재는
   backend/scripts/load_legal_articles.py.
2. 고지서 글자에서 「○○법 제○조」를 먼저 찾아 번호로 거르고, 그다음 문장 유사도로 고른다.
   지금은 조문 번호 인용이 있을 때만 찾는다 — 유사도 검색(인용이 없어도 비슷한 내용을
   찾는 것)은 진짜 임베딩이 필요해서 아직 배관이 없다(아래 `add_article()` 참고).
3. 찾은 근거는 schema.Basis 로 돌려준다. quote(원문 문장)가 비면 agent 가 그 풀이를 버린다.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import chromadb

from .schema import Basis

log = logging.getLogger(__name__)

_CHROMA_DIR = Path(__file__).resolve().parents[2] / "data" / "legal" / "chroma"
# 이름에 "dummy"를 박아 둔다 — 진짜 임베딩(예: 384차원)으로 바꾸면 컬렉션을 통째로
# 새로 만들어야 하는데(Chroma는 컬렉션의 임베딩 차원을 처음 넣을 때 고정한다), 이름이
# 같으면 차원 불일치 에러가 난다. 이름을 바꾸면 자연스럽게 새 컬렉션으로 분리된다.
_COLLECTION_NAME = "legal_articles_dummy"

# "국민건강보험법 제80조", "지방세법 제15조", "국민건강보험법 제80조의2" 같은 인용을 찾는다.
_CITATION_RE = re.compile(r"([가-힣]+법)\s*제\s*(\d+)\s*조(?:\s*의\s*(\d+))?")

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


def _format_law(law_name: str, article_no: str) -> str:
    """"80의2" → "제80조의2", "80" → "제80조". article_no에 "의"가 섞여 있으면
    조 번호와 분리해서 올바른 위치에 "조"를 끼워 넣는다."""
    if "의" in article_no:
        main, sub = article_no.split("의", 1)
        return f"{law_name} 제{main}조의{sub}"
    return f"{law_name} 제{article_no}조"


def _citations(text: str) -> list[tuple[str, str]]:
    """고지서 글자에서 "○○법 제○조"(「의N」 포함) 패턴을 전부 뽑는다.

    "제80조의2"를 "80"으로 뭉뚱그리면 실제로는 다른 조문(제80조)이 근거로 잘못
    붙는다 — 틀린 근거는 근거 없음보다 나쁘다. 같은 인용이 본문에 두 번 나와도
    순서를 지키며 중복을 제거한다(dict.fromkeys) — 안 그러면 같은 근거가 plain
    요약 3줄 중 여러 칸을 차지한다.
    """
    found = [
        (law_name, f"{article_no}의{sub_no}" if sub_no else article_no)
        for law_name, article_no, sub_no in _CITATION_RE.findall(text)
    ]
    return list(dict.fromkeys(found))


def find_basis(text: str) -> list[Basis]:
    """고지서 글자에 맞는 근거 목록을 찾는다.

    조문 번호 인용이 본문에 있을 때만 찾는다(유사도 검색은 아직 없음 — 모듈 docstring
    참고). 컬렉션에 없는 조문이면 빈 목록을 낸다 — 근거 없는 문장을 지어내지 않는다.

    Chroma 쪽 실패(디스크 권한, DB 파일 깨짐 등)는 여기서 삼킨다 — agent.decode()가
    예외 처리 없이 바로 부르기 때문에, 여기서 안 막으면 근거 하나 때문에 사진 해독
    전체가 500이 된다. extract.py의 실패 처리와 같은 패턴.
    """
    try:
        collection = _collection()
        results: list[Basis] = []
        for law_name, article_no in _citations(text):
            hit = collection.get(
                where={"$and": [{"law_name": {"$eq": law_name}}, {"article_no": {"$eq": article_no}}]}
            )
            for doc, meta in zip(hit["documents"], hit["metadatas"], strict=True):
                results.append(Basis(claim=meta["claim"], quote=doc, law=_format_law(law_name, article_no)))

        return results
    except Exception:
        log.exception("근거 검색 실패 — 근거 없이 넘어감")
        return []
