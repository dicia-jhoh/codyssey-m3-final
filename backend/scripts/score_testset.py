"""고지서 테스트셋 정확도 측정 — data/testset/README.md의 성공 기준(90% 이상)을 잰다.

사용:
    cd backend
    LLM_API_KEY=... python -m scripts.score_testset

labels.jsonl 모양은 data/testset/labels.example.jsonl 참고. 사진은 labels.jsonl 과 같은
폴더 기준 상대 경로로 찾는다(실물 사진은 개인정보라 커밋하지 않는다).

이 숫자는 발표·평가에 그대로 쓰인다 — 그래서 점수가 실제보다 높게 나오는 경로를
의도적으로 막아 둔다(아래 함수 docstring 참고).
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from app import ROOT
from app.agent import decode
from app.schema import Decoded

_DEFAULT_LABELS = ROOT / "data" / "testset" / "labels.jsonl"
TARGET_ACCURACY = 0.9  # 기획서 성공 기준 「추출 정확도 90% 이상」


@dataclass
class ImageScore:
    image: str
    correct: int = 0
    total: int = 0
    details: list[str] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0


def _fuzzy_match(expected: str, candidates: list[str]) -> bool:
    """서류처럼 자유 문장인 항목은 부분 일치면 맞힌 걸로 친다 — 단, 둘 중 하나가
    2글자 이하면 완전 일치만 인정한다(짧은 문자열은 부분 일치가 거의 항상 맞아버려서
    점수가 부풀려진다. 예: 기대값 "서"가 아무 서류 텍스트에나 다 들어있음)."""
    for c in candidates:
        if not c:
            continue
        if len(expected) <= 2 or len(c) <= 2:
            if expected == c:
                return True
        elif expected in c:
            return True
    return False


def score_one(label: dict, result: Decoded | None) -> ImageScore:
    """라벨(정답) 한 줄과 Decoded(추출 결과) 하나를 맞춰본다.

    result가 None이면(추출 실패로 샘플 모드에 빠졌거나 이미지 파일이 없음) 그 라벨의
    항목 전부를 오답으로 센다 — 실패한 사진을 분모에서 빼면(건너뛰면) 나머지만으로
    정확도가 부풀려진다(30장 중 10장 실패해도 20장만으로 "95% 달성"이 나올 수 있음).

    금액·기한은 재현율(정답을 다 뽑았나)뿐 아니라 정밀도(엉뚱한 값을 안 뽑았나)도
    본다 — 정답 기한 1개에 엉뚱한 기한을 더 뽑아도 재현율만 보면 100%가 나오는데,
    틀린 기한은 기한 없음보다 위험하다(D-day 알림이 틀어짐).

    할 일은 제목이 아니라 (기한, 금액) 쌍으로 비교한다 — 제목은 rag 연동 전까지
    "{doc_type} 돈 내기"처럼 구체화되지 않은 상태라(agent.py의 _title_for 참고)
    제목 비교는 지금 구조에서는 늘 0점이 나온다. 지금 잴 수 있는 건 카드 내용이
    맞게 만들어졌는지다.
    """
    score = ImageScore(image=label["image"])
    expected_money = label.get("money", [])
    expected_dates = label.get("deadlines", [])
    expected_docs = label.get("documents", [])
    expected_todos = label.get("todos", [])  # [{"due": ..., "amount": ...}, ...]

    if result is None:
        score.total = (
            len(expected_money) + len(expected_dates) + len(expected_docs) + len(expected_todos)
        )
        score.details.append("추출 실패(샘플 모드) 또는 이미지 없음 — 전부 오답 처리")
        return score

    got_money = [m.value for m in result.marks if m.kind == "money"]
    got_dates = [m.value for m in result.marks if m.kind == "deadline"]
    got_docs = [m.text for m in result.marks if m.kind == "document"]
    got_todos = [(t.due, t.amount) for t in result.todos]

    _score_both_ways(score, [str(a) for a in expected_money], got_money, "금액", "원")
    _score_both_ways(score, expected_dates, got_dates, "기한")
    for doc in expected_docs:
        _count(score, _fuzzy_match(doc, got_docs), f"서류 놓침: {doc}")
    for todo in expected_todos:
        due, amount = todo.get("due"), todo.get("amount")
        _count(score, (due, amount) in got_todos, f"할 일 카드 놓침: 기한={due} 금액={amount}")
    return score


def _count(score: ImageScore, hit: bool, miss_note: str) -> None:
    score.total += 1
    if hit:
        score.correct += 1
    else:
        score.details.append(miss_note)


def _score_both_ways(
    score: ImageScore, expected: list[str], got: list[str], name: str, unit: str = ""
) -> None:
    """재현율(정답을 다 뽑았나)과 정밀도(엉뚱한 값을 더 뽑았나)를 같은 분모에 센다."""
    for value in expected:
        _count(score, value in got, f"{name} 놓침: {value}{unit}")
    for value in got:
        if value not in expected:
            score.total += 1
            score.details.append(f"잘못 뽑음({name}): {value}{unit}")


def _read_labels(path: Path) -> list[dict]:
    labels = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            labels.append(json.loads(line))
    return labels


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", type=Path, default=_DEFAULT_LABELS, help="labels.jsonl 경로")
    args = parser.parse_args(argv)

    if not args.labels.exists():
        print(f"[!] 라벨 파일 없음: {args.labels}")
        print("    data/testset/README.md 참고 — 실제 고지서 사진·정답을 먼저 채워야 함")
        return 1

    if not os.environ.get("LLM_API_KEY"):
        print("[!] LLM_API_KEY 없음 — 샘플 모드로는 의미 있는 정확도를 잴 수 없음")
        return 1

    scores: list[ImageScore] = []
    failures = 0
    doc_types: list[bool] = []  # 판별을 맞혔나 — 참고용, 전체 정확도엔 넣지 않는다
    for label in _read_labels(args.labels):
        result = _decode_label(args.labels.parent, label)
        failures += result is None
        if result is not None and label.get("doc_type"):
            doc_types.append(result.doc_type == label["doc_type"])
        score = score_one(label, result)
        scores.append(score)
        _print_score(score)

    if not scores:
        print("[!] 채점한 이미지가 없음")
        return 1
    _print_summary(scores, failures, doc_types)
    return 0


def _decode_label(dataset_root: Path, label: dict) -> Decoded | None:
    """라벨의 사진을 해독한다. 사진이 없거나 샘플 모드에 빠지면 None(전부 오답으로 센다)."""
    image_path = dataset_root / label["image"]
    if not image_path.exists():
        print(f"[!] 이미지 없음: {image_path}")
        return None
    result = decode(image_path.read_bytes())
    if result.sample:
        print(f"[!] {label['image']} — 추출 실패로 샘플 모드에 빠짐")
        return None
    return result


def _print_score(score: ImageScore) -> None:
    print(f"{score.image}: {score.correct}/{score.total} ({score.accuracy:.0%})")
    for detail in score.details:
        print(f"  - {detail}")


def _print_summary(scores: list[ImageScore], failures: int, doc_types: list[bool]) -> None:
    total_correct = sum(s.correct for s in scores)
    total_items = sum(s.total for s in scores)
    overall = total_correct / total_items if total_items else 0.0
    verdict = "달성" if overall >= TARGET_ACCURACY else "미달"
    target = f"기준 {TARGET_ACCURACY:.0%} {verdict}"
    print(f"\n전체: {total_correct}/{total_items} ({overall:.1%}) — {target}")
    print(f"추출 실패/이미지 없음: {failures}/{len(scores)}장")
    if doc_types:
        print(f"문서 종류 판별(참고용, 전체 정확도엔 미포함): {sum(doc_types)}/{len(doc_types)}")


if __name__ == "__main__":
    raise SystemExit(main())
