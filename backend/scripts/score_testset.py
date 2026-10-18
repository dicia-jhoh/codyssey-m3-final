"""고지서 테스트셋 정확도 측정 — data/testset/README.md의 성공 기준(90% 이상)을 잰다.

사용:
    cd backend
    LLM_API_KEY=... python scripts/score_testset.py

labels.jsonl 모양은 data/testset/labels.example.jsonl 참고. 아직 실제 라벨 파일
(data/testset/labels.jsonl)과 사진(data/testset/images/)이 없다 — 김기훈이 채우면
바로 돌아간다.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ 를 import 경로에 추가

from app.agent import decode  # noqa: E402
from app.schema import Decoded  # noqa: E402

_DEFAULT_LABELS = Path(__file__).resolve().parents[2] / "data" / "testset" / "labels.jsonl"


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
    """서류·할 일처럼 자유 문장인 항목은 부분 일치면 맞힌 걸로 친다(완전 일치는 너무 깐깐함)."""
    return any(expected in c or c in expected for c in candidates if c)


def score_one(label: dict, result: Decoded) -> ImageScore:
    """라벨(정답) 한 줄과 Decoded(추출 결과) 하나를 맞춰본다.

    금액·기한은 README 기준대로 완전 일치만 맞힌 것으로 친다(원 단위·날짜까지 같아야).
    서류·할 일은 의미가 같은 다른 문장으로 나올 수 있어 부분 일치로 느슨하게 본다.
    """
    score = ImageScore(image=label["image"])

    extracted_money = [m.value for m in result.marks if m.kind == "money"]
    for amount in label.get("money", []):
        score.total += 1
        if str(amount) in extracted_money:
            score.correct += 1
        else:
            score.details.append(f"금액 놓침: {amount}원")

    extracted_dates = [m.value for m in result.marks if m.kind == "deadline"]
    for due in label.get("deadlines", []):
        score.total += 1
        if due in extracted_dates:
            score.correct += 1
        else:
            score.details.append(f"기한 놓침: {due}")

    extracted_docs = [m.text for m in result.marks if m.kind == "document"]
    for doc in label.get("documents", []):
        score.total += 1
        if _fuzzy_match(doc, extracted_docs):
            score.correct += 1
        else:
            score.details.append(f"서류 놓침: {doc}")

    extracted_todos = [t.title for t in result.todos]
    for todo in label.get("todos", []):
        score.total += 1
        if _fuzzy_match(todo, extracted_todos):
            score.correct += 1
        else:
            score.details.append(f"할 일 놓침: {todo}")

    return score


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

    dataset_root = args.labels.parent
    scores: list[ImageScore] = []

    for label in _read_labels(args.labels):
        image_path = dataset_root / label["image"]
        if not image_path.exists():
            print(f"[!] 이미지 없음, 건너뜀: {image_path}")
            continue

        result = decode(image_path.read_bytes())
        if result.sample:
            print(f"[!] {label['image']} — 추출 실패로 샘플 모드에 빠짐, 건너뜀")
            continue

        score = score_one(label, result)
        scores.append(score)
        print(f"{label['image']}: {score.correct}/{score.total} ({score.accuracy:.0%})")
        for detail in score.details:
            print(f"  - {detail}")

    if not scores:
        print("[!] 채점한 이미지가 없음")
        return 1

    total_correct = sum(s.correct for s in scores)
    total_items = sum(s.total for s in scores)
    overall = total_correct / total_items if total_items else 0.0
    verdict = "달성" if overall >= 0.9 else "미달"
    print(f"\n전체: {total_correct}/{total_items} ({overall:.1%}) — 기준 90% {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
