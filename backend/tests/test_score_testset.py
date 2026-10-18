from app.schema import Decoded, Mark, Todo
from scripts.score_testset import _fuzzy_match, score_one


def _decoded(**marks_and_todos) -> Decoded:
    return Decoded(
        doc_type="고지서",
        title="t",
        plain=[],
        marks=marks_and_todos.get("marks", []),
        todos=marks_and_todos.get("todos", []),
        basis=[],
    )


def test_fuzzy_match_substring_for_longer_strings():
    assert _fuzzy_match("납부서", ["납부서(뒷면)"])
    assert not _fuzzy_match("납부서", ["차량등록증"])


def test_fuzzy_match_requires_exact_match_for_short_strings():
    # 둘 중 하나가 2글자 이하면 부분 일치를 허용 안 한다 — 안 그러면 "서" 같은
    # 기대값이 아무 서류 텍스트에나 다 매치돼서 점수가 부풀려진다.
    assert not _fuzzy_match("서", ["납부서(뒷면)"])
    assert _fuzzy_match("서", ["서"])


def test_score_one_all_correct():
    label = {
        "image": "001.jpg",
        "money": [48200],
        "deadlines": ["2026-10-31"],
        "documents": ["납부서"],
        "todos": [{"due": "2026-10-31", "amount": 48200}],
    }
    result = _decoded(
        marks=[
            Mark(kind="money", text="금 48,200원", value="48200", bbox=[0, 0, 0.1, 0.1]),
            Mark(kind="deadline", text="2026.10.31까지", value="2026-10-31", bbox=[0, 0, 0.1, 0.1]),
            Mark(kind="document", text="납부서(뒷면)", value="", bbox=[0, 0, 0.1, 0.1]),
        ],
        todos=[Todo(title="고지서 금액 내기", due="2026-10-31", amount=48200, how="")],
    )

    score = score_one(label, result)

    assert score.correct == 4
    assert score.total == 4
    assert score.accuracy == 1.0
    assert score.details == []


def test_score_one_misses_wrong_amount():
    label = {"image": "001.jpg", "money": [48200]}
    result = _decoded(marks=[Mark(kind="money", text="x", value="99999", bbox=[0, 0, 0.1, 0.1])])

    score = score_one(label, result)

    # 정답(48200)을 못 뽑은 것 1건 + 엉뚱한 값(99999)을 뽑은 것 1건 = 분모 2, 정답 0
    assert score.correct == 0
    assert score.total == 2
    assert "금액 놓침: 48200원" in score.details
    assert "잘못 뽑음(금액): 99999원" in score.details


def test_score_one_penalizes_extra_wrong_deadline():
    # 정답 기한 1개는 맞혔지만, 엉뚱한 기한을 하나 더 뽑으면 그만큼 감점된다.
    label = {"image": "001.jpg", "deadlines": ["2026-10-31"]}
    result = _decoded(
        marks=[
            Mark(kind="deadline", text="a", value="2026-10-31", bbox=[0, 0, 0.1, 0.1]),
            Mark(kind="deadline", text="b", value="2099-01-01", bbox=[0, 0, 0.1, 0.1]),
        ]
    )

    score = score_one(label, result)

    assert score.correct == 1
    assert score.total == 2
    assert "잘못 뽑음(기한): 2099-01-01" in score.details


def test_score_one_handles_empty_label_fields():
    score = score_one({"image": "001.jpg"}, _decoded())
    assert score.total == 0
    assert score.accuracy == 0.0


def test_score_one_treats_failed_extraction_as_all_wrong():
    # result=None(샘플 모드 폴백·이미지 없음)이면 라벨의 모든 항목을 오답으로 센다 —
    # 실패한 사진을 분모에서 빼면 나머지만으로 정확도가 부풀려진다(이슈 #23-1).
    label = {
        "image": "001.jpg",
        "money": [1000],
        "deadlines": ["2026-01-01"],
        "documents": ["서류"],
        "todos": [{"due": "2026-01-01", "amount": 1000}],
    }

    score = score_one(label, None)

    assert score.correct == 0
    assert score.total == 4
    assert "전부 오답 처리" in score.details[0]


def test_score_one_matches_todo_by_due_and_amount_not_title():
    # #17 이후 제목이 "{doc_type} 금액 내기"로 바뀌어서 라벨 예시의 "건강보험료 내기"와
    # 절대 안 맞는다 — 그래서 제목이 아니라 (기한, 금액) 쌍으로 비교한다(이슈 #23-3).
    label = {"image": "001.jpg", "todos": [{"due": "2026-10-31", "amount": 48200}]}
    result = _decoded(
        todos=[Todo(title="고지서 금액 내기", due="2026-10-31", amount=48200, how="")]
    )

    score = score_one(label, result)

    assert score.correct == 1
    assert score.total == 1
