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


def test_fuzzy_match_substring_either_direction():
    assert _fuzzy_match("납부서", ["납부서(뒷면)"])
    assert _fuzzy_match("신분증 사본", ["신분증"])
    assert not _fuzzy_match("납부서", ["차량등록증"])


def test_score_one_all_correct():
    label = {
        "image": "001.jpg",
        "money": [48200],
        "deadlines": ["2026-10-31"],
        "documents": ["납부서"],
        "todos": ["건강보험료 내기"],
    }
    result = _decoded(
        marks=[
            Mark(kind="money", text="금 48,200원", value="48200", bbox=[0, 0, 0.1, 0.1]),
            Mark(kind="deadline", text="2026.10.31까지", value="2026-10-31", bbox=[0, 0, 0.1, 0.1]),
            Mark(kind="document", text="납부서(뒷면)", value="", bbox=[0, 0, 0.1, 0.1]),
        ],
        todos=[Todo(title="건강보험료 내기", due="2026-10-31", amount=48200, how="")],
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

    assert score.correct == 0
    assert score.total == 1
    assert "금액 놓침: 48200원" in score.details


def test_score_one_handles_empty_label_fields():
    score = score_one({"image": "001.jpg"}, _decoded())
    assert score.total == 0
    assert score.accuracy == 0.0
