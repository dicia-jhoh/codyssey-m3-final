from app.agent import _todos_from_marks, classify, decode
from app.schema import Mark, Todo


def test_classify_detects_bill_by_keyword():
    assert classify("납부기한: 2026.10.31까지") == "고지서"


def test_classify_defaults_to_notice():
    assert classify("아무 안내") == "안내문"


def test_todos_from_marks_pairs_money_with_nearest_deadline():
    marks = [
        Mark(kind="money", text="금 48,200원", value="48200", bbox=[0.6, 0.18, 0.3, 0.06]),
        Mark(kind="deadline", text="2026.10.31까지", value="2026-10-31", bbox=[0.6, 0.26, 0.3, 0.06]),
        Mark(kind="document", text="신분증", value="", bbox=[0.1, 0.7, 0.5, 0.08]),
    ]
    todos = _todos_from_marks("고지서", marks)
    assert todos == [Todo(title="고지서 납부하기", due="2026-10-31", amount=48200, how="은행 또는 앱 납부")]


def test_todos_from_marks_pairs_each_money_with_closest_deadline():
    # 두 금액·두 기한이 섞여 있어도 세로 위치가 가까운 것끼리 짝짓는다.
    marks = [
        Mark(kind="money", text="1차", value="10000", bbox=[0, 0.1, 0.1, 0.05]),
        Mark(kind="deadline", text="1차기한", value="2026-01-01", bbox=[0, 0.12, 0.1, 0.05]),
        Mark(kind="money", text="2차", value="20000", bbox=[0, 0.8, 0.1, 0.05]),
        Mark(kind="deadline", text="2차기한", value="2026-02-02", bbox=[0, 0.82, 0.1, 0.05]),
    ]
    todos = _todos_from_marks("고지서", marks)
    assert len(todos) == 2
    assert todos[0].amount == 10000 and todos[0].due == "2026-01-01"
    assert todos[1].amount == 20000 and todos[1].due == "2026-02-02"


def test_todos_from_marks_handles_no_deadline():
    marks = [Mark(kind="money", text="금 1,000원", value="1000", bbox=[0, 0, 0.1, 0.1])]
    todos = _todos_from_marks("고지서", marks)
    assert todos == [Todo(title="고지서 납부하기", due=None, amount=1000, how="은행 또는 앱 납부")]


def test_todos_from_marks_empty_when_no_money():
    marks = [Mark(kind="document", text="신분증", value="", bbox=[0, 0, 0.1, 0.1])]
    assert _todos_from_marks("고지서", marks) == []


def test_decode_without_api_key_returns_sample(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    result = decode(b"fake")
    assert result.sample is True


def test_decode_builds_todos_from_extracted_marks(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "dummy")
    monkeypatch.setattr(
        "app.agent.extract.extract",
        lambda image, api_key: (
            "납부금액: 금 48,200원\n납부기한: 2026.10.31까지",
            [
                Mark(kind="money", text="금 48,200원", value="48200", bbox=[0.6, 0.18, 0.3, 0.06]),
                Mark(kind="deadline", text="2026.10.31까지", value="2026-10-31", bbox=[0.6, 0.26, 0.3, 0.06]),
            ],
        ),
    )
    result = decode(b"fake")
    assert result.sample is False
    assert result.doc_type == "고지서"
    assert len(result.todos) == 1
    assert result.todos[0].amount == 48200
    assert result.todos[0].due == "2026-10-31"
