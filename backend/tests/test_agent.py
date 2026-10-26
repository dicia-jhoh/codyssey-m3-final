from app.agent import _how, _preparation_note, _todos_from_marks, classify, decode
from app.schema import Mark, Todo


def test_classify_detects_bill_by_keyword():
    assert classify("납부기한: 2026.10.31까지") == "고지서"


def test_classify_defaults_to_notice():
    assert classify("아무 안내") == "안내문"


def test_todos_from_marks_pairs_money_with_nearest_deadline():
    # document Mark("신분증")가 있으면 how에 준비물 문구가 붙는다(이슈 #20-4).
    marks = [
        Mark(kind="money", text="금 48,200원", value="48200", bbox=[0.6, 0.18, 0.3, 0.06]),
        Mark(kind="deadline", text="2026.10.31까지", value="2026-10-31", bbox=[0.6, 0.26, 0.3, 0.06]),
        Mark(kind="document", text="신분증", value="", bbox=[0.1, 0.7, 0.5, 0.08]),
    ]
    todos = _todos_from_marks("고지서", marks)
    assert todos == [
        Todo(title="고지서 돈 내기", due="2026-10-31", amount=48200, how="은행 또는 앱 납부 · 신분증 챙기기")
    ]


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
    assert todos == [Todo(title="고지서 돈 내기", due=None, amount=1000, how="은행 또는 앱 납부")]


def test_todos_from_marks_empty_when_no_money_or_deadline():
    marks = [Mark(kind="document", text="신분증", value="", bbox=[0, 0, 0.1, 0.1])]
    assert _todos_from_marks("고지서", marks) == []


def test_todos_from_marks_makes_card_for_deadline_only_document():
    # 신청서처럼 돈 없이 기한만 있는 문서도 카드가 나와야 한다(이슈 #20-1).
    marks = [Mark(kind="deadline", text="10월 31일까지", value="2026-10-31", bbox=[0, 0, 0.1, 0.1])]
    todos = _todos_from_marks("신청서", marks)
    assert todos == [Todo(title="신청서 내기", due="2026-10-31", amount=None, how="")]


def test_todos_from_marks_deadline_only_uses_document_marks_as_how():
    # 돈 없이 기한+서류만 있으면 how가 준비물 문구를 받는다(이슈 #20-4).
    marks = [
        Mark(kind="deadline", text="10월 31일까지", value="2026-10-31", bbox=[0, 0, 0.1, 0.1]),
        Mark(kind="document", text="가족관계증명서", value="", bbox=[0, 0.5, 0.1, 0.1]),
    ]
    todos = _todos_from_marks("신청서", marks)
    assert todos == [
        Todo(title="신청서 내기", due="2026-10-31", amount=None, how="가족관계증명서 챙기기")
    ]


def test_preparation_note_joins_multiple_document_marks():
    marks = [
        Mark(kind="document", text="신분증", value="", bbox=[0, 0, 0.1, 0.1]),
        Mark(kind="document", text="도장", value="", bbox=[0, 0.5, 0.1, 0.1]),
        Mark(kind="money", text="무시됨", value="1", bbox=[0, 0, 0.1, 0.1]),
    ]
    assert _preparation_note(marks) == "신분증, 도장 챙기기"


def test_preparation_note_empty_without_document_marks():
    assert _preparation_note([Mark(kind="money", text="x", value="1", bbox=[0, 0, 0.1, 0.1])]) == ""


def test_how_drops_empty_parts():
    assert _how("은행 또는 앱 납부", "") == "은행 또는 앱 납부"
    assert _how("", "신분증 챙기기") == "신분증 챙기기"
    assert _how("", "") == ""


def test_todos_from_marks_deadline_only_title_for_non_application_doc():
    marks = [Mark(kind="deadline", text="11월 3일까지", value="2026-11-03", bbox=[0, 0, 0.1, 0.1])]
    todos = _todos_from_marks("가정통신문", marks)
    assert todos[0].title == "가정통신문 내기"


def test_todos_from_marks_ignores_deadline_too_far_from_money():
    # 금액 바로 옆이 아니라 문서 맨 아래 멀리 떨어진 기한(예: 이의신청 기한)은 안 붙는다.
    # 대신 짝 못 찾은 deadline은 자기 카드를 따로 받는다(이슈 #20-3).
    marks = [
        Mark(kind="money", text="금 48,200원", value="48200", bbox=[0, 0.1, 0.1, 0.05]),
        Mark(kind="deadline", text="이의신청 기한", value="2026-12-31", bbox=[0, 0.9, 0.1, 0.05]),
    ]
    todos = _todos_from_marks("고지서", marks)
    assert len(todos) == 2
    money_todo = next(t for t in todos if t.amount == 48200)
    assert money_todo.due is None
    deadline_todo = next(t for t in todos if t.amount is None)
    assert deadline_todo.due == "2026-12-31"


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
