"""고지서 테스트셋 정확도 측정 — data/testset/README.md의 성공 기준(90% 이상)을 잰다.

사용:
    cd backend
    LLM_API_KEY=... python -m scripts.score_testset             # 이 컴퓨터에서 해독
    python -m scripts.score_testset --server http://localhost:8037 \
        --labels ../data/testset/synthetic/labels.jsonl --out score.json   # 배포 서버로 해독

labels.jsonl 모양은 data/testset/labels.example.jsonl 참고. 사진은 labels.jsonl 과 같은
폴더 기준 상대 경로로 찾는다(실물 사진은 개인정보라 커밋하지 않는다).

이 숫자는 발표·평가에 그대로 쓰인다 — 그래서 점수가 실제보다 높게 나오는 경로를
의도적으로 막아 둔다(아래 함수 docstring 참고).
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import httpx

from app import ROOT
from app.agent import decode
from app.schema import Decoded

_DEFAULT_LABELS = ROOT / "data" / "testset" / "labels.jsonl"
TARGET_ACCURACY = 0.9  # 기획서 성공 기준 「추출 정확도 90% 이상」
SERVER_SPACING_SECONDS = 6.5  # 서버 요청 제한 = IP 하나당 60초에 10번
SERVER_TIMEOUT_SECONDS = 120


@dataclass
class ImageScore:
    image: str
    correct: int = 0
    total: int = 0
    details: list[str] = field(default_factory=list)
    bill: str = ""  # 고지서 종류(라벨의 bill) — 종류별 정확도용
    seconds: float | None = None  # 서버로 잰 응답 시간

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
    score = ImageScore(image=label["image"], bill=label.get("bill", ""))
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
    parser.add_argument(
        "--server", help="배포 서버 주소 — 그 서버의 /decode 로 잰다(응답 시간 포함)"
    )
    parser.add_argument("--out", type=Path, help="요약 JSON 저장 경로")
    args = parser.parse_args(argv)

    if not args.labels.exists():
        print(f"[!] 라벨 파일 없음: {args.labels}")
        print("    data/testset/README.md 참고 — 실제 고지서 사진·정답을 먼저 채워야 함")
        return 1

    if not args.server and not os.environ.get("LLM_API_KEY"):
        print("[!] LLM_API_KEY 없음 — 샘플 모드로는 의미 있는 정확도를 잴 수 없음")
        return 1

    scores: list[ImageScore] = []
    failures = 0
    doc_types: list[bool] = []  # 판별을 맞혔나 — 참고용, 전체 정확도엔 넣지 않는다
    for i, label in enumerate(_read_labels(args.labels)):
        if args.server and i:
            time.sleep(SERVER_SPACING_SECONDS)
        started = time.monotonic()
        result = _decode_label(args.labels.parent, label, args.server)
        seconds = time.monotonic() - started
        failures += result is None
        if result is not None and label.get("doc_type"):
            doc_types.append(result.doc_type == label["doc_type"])
        score = score_one(label, result)
        if args.server and result is not None:
            score.seconds = seconds
        scores.append(score)
        _print_score(score)

    if not scores:
        print("[!] 채점한 이미지가 없음")
        return 1
    summary = _summary(scores, failures, doc_types)
    _print_summary(summary)
    if args.out:
        summary["server"] = args.server or ""
        args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", "utf-8")
    return 0


def _decode_label(dataset_root: Path, label: dict, server: str | None) -> Decoded | None:
    """라벨의 사진을 해독한다. 사진이 없거나 샘플 모드에 빠지면 None(전부 오답으로 센다)."""
    image_path = dataset_root / label["image"]
    if not image_path.exists():
        print(f"[!] 이미지 없음: {image_path}")
        return None
    try:
        result = _decode_on(server, image_path) if server else decode(image_path.read_bytes())
    except httpx.HTTPError as error:  # 한 장의 429·5xx·시간 초과로 측정 전체를 멈추지 않는다
        print(f"[!] {label['image']} — 서버 해독 실패({type(error).__name__}), 전부 오답 처리")
        return None
    if result.sample:
        print(f"[!] {label['image']} — 추출 실패로 샘플 모드에 빠짐")
        return None
    return result


def _decode_on(server: str, image_path: Path) -> Decoded:
    files = {"file": (image_path.name, image_path.read_bytes(), "image/jpeg")}
    url = f"{server.rstrip('/')}/decode"
    response = httpx.post(url, files=files, timeout=SERVER_TIMEOUT_SECONDS)
    response.raise_for_status()
    return Decoded.model_validate(response.json())


def _print_score(score: ImageScore) -> None:
    print(f"{score.image}: {score.correct}/{score.total} ({score.accuracy:.0%})")
    for detail in score.details:
        print(f"  - {detail}")


def _summary(scores: list[ImageScore], failures: int, doc_types: list[bool]) -> dict:
    correct = sum(s.correct for s in scores)
    total = sum(s.total for s in scores)
    by_bill: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for s in scores:
        if s.bill:
            by_bill[s.bill][0] += s.correct
            by_bill[s.bill][1] += s.total
    seconds = [s.seconds for s in scores if s.seconds is not None]
    return {
        "measured_on": date.today().isoformat(),
        "items": {
            "correct": correct,
            "total": total,
            "accuracy": correct / total if total else 0.0,
        },
        "images": {
            "all_correct": sum(s.correct == s.total > 0 for s in scores),
            "total": len(scores),
        },
        "failures": failures,
        "doc_type": {"correct": sum(doc_types), "total": len(doc_types)},
        "by_bill": {k: {"correct": c, "total": t} for k, (c, t) in by_bill.items()},
        "seconds": {"mean": statistics.mean(seconds), "max": max(seconds)} if seconds else None,
    }


def _print_summary(summary: dict) -> None:
    items, images = summary["items"], summary["images"]
    verdict = "달성" if items["accuracy"] >= TARGET_ACCURACY else "미달"
    target = f"기준 {TARGET_ACCURACY:.0%} {verdict}"
    print(f"\n전체: {items['correct']}/{items['total']} ({items['accuracy']:.1%}) — {target}")
    print(f"모두 맞힌 사진: {images['all_correct']}/{images['total']}장")
    print(f"추출 실패/이미지 없음: {summary['failures']}/{images['total']}장")
    for bill, s in summary["by_bill"].items():
        accuracy = s["correct"] / s["total"] if s["total"] else 0.0
        print(f"  {bill}: {s['correct']}/{s['total']} ({accuracy:.1%})")
    if summary["doc_type"]["total"]:
        judged = summary["doc_type"]
        print(
            f"문서 종류 판별(참고용, 전체 정확도엔 미포함): {judged['correct']}/{judged['total']}"
        )
    if summary["seconds"]:
        mean, longest = summary["seconds"]["mean"], summary["seconds"]["max"]
        print(f"응답 시간: 평균 {mean:.1f}초, 최대 {longest:.1f}초")


if __name__ == "__main__":
    raise SystemExit(main())
