import pytest

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
        Mark(
            kind="deadline", text="2026.10.31까지", value="2026-10-31", bbox=[0.6, 0.26, 0.3, 0.06]
        ),
        Mark(kind="document", text="신분증", value="", bbox=[0.1, 0.7, 0.5, 0.08]),
    ]
    todos = _todos_from_marks("고지서", marks)
    assert todos == [
        Todo(
            title="고지서 돈 내기",
            due="2026-10-31",
            amount=48200,
            how="은행 또는 앱 납부 · 신분증 챙기기",
        )
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
                Mark(
                    kind="deadline",
                    text="2026.10.31까지",
                    value="2026-10-31",
                    bbox=[0.6, 0.26, 0.3, 0.06],
                ),
            ],
        ),
    )
    result = decode(b"fake")
    assert result.sample is False
    assert result.doc_type == "고지서"
    assert len(result.todos) == 1
    assert result.todos[0].amount == 48200
    assert result.todos[0].due == "2026-10-31"


def test_classify_fine_before_bill_because_fines_also_say_pay():
    assert classify("과태료 부과 사전통지서\n납부기한: 2026.11.20") == "과태료"


_FINE_TEXT = "과태료 부과 사전통지서\n과태료: 40,000원\n의견 제출 기한: 2026.11.20"


def _fine_marks(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "dummy")
    monkeypatch.setattr("app.agent.extract.extract", lambda image, api_key: (_FINE_TEXT, []))


def test_fine_notice_gets_reply_draft_and_reduction_basis(monkeypatch):
    from app import rag, reply
    from scripts.load_legal_articles import load

    load()  # 적재된 조문(의견 제출·감경 포함)을 격리된 Chroma 에
    _fine_marks(monkeypatch)
    sent = []
    monkeypatch.setattr(reply, "_ask", lambda text, key: sent.append(text) or "의견 제출서 초안")

    result = decode(b"fake")

    assert result.doc_type == "과태료" and result.reply_needed
    assert result.reply_draft == "의견 제출서 초안"
    assert sent == [_FINE_TEXT]  # LLM 에는 가린 글자만 간다
    laws = [b.law for b in result.basis]
    assert laws == [
        "질서위반행위규제법 제16조",
        "질서위반행위규제법 제18조",
        "질서위반행위규제법 시행령 제5조",
    ]
    assert "100분의 20" in result.basis[2].quote
    assert rag.article("없는법", "1") is None


def test_reply_draft_falls_back_to_blank_form_when_llm_fails(monkeypatch):
    from app import reply

    _fine_marks(monkeypatch)

    def broken(text, key):
        raise RuntimeError("down")

    monkeypatch.setattr(reply, "_ask", broken)
    assert decode(b"fake").reply_draft == reply.TEMPLATE


def test_bill_gets_no_reply_draft(monkeypatch):
    from app import reply

    monkeypatch.setenv("LLM_API_KEY", "dummy")
    monkeypatch.setattr(
        "app.agent.extract.extract", lambda image, api_key: ("납부기한 10월 31일", [])
    )
    monkeypatch.setattr(reply, "_ask", lambda text, key: pytest.fail("고지서엔 초안을 쓰지 않는다"))
    result = decode(b"fake")
    assert result.reply_draft == "" and not result.reply_needed


def test_same_amount_printed_three_times_is_one_card():
    """과태료 고지서는 금액을 표·본문·납부서에 찍는다 — 실측(b26)에서 같은 카드가 넷 나왔다."""
    marks = [
        Mark(kind="money", text="40,000원", value="40000", bbox=[0.1, y, 0.2, 0.05])
        for y in (0.30, 0.32, 0.34)
    ] + [Mark(kind="deadline", text="2026.11.26", value="2026-11-26", bbox=[0.1, 0.31, 0.2, 0.05])]
    assert _todos_from_marks("과태료", marks) == [
        Todo(title="과태료 돈 내기", due="2026-11-26", amount=40000, how="은행 또는 앱 납부")
    ]


def test_notice_that_only_warns_about_a_fine_is_not_a_fine_notice():
    """「…하면 과태료가 부과됩니다」 한 줄만 있는 안내는 과태료 고지서가 아니다."""
    text = "전입신고 안내\n14일 안에 신고하지 않으면 과태료가 부과됩니다.\n신청서를 내 주세요."
    assert classify(text) == "신청서"
    assert classify("주정차위반 과태료 부과 고지서\n과태료 금액 40,000원") == "과태료"
    assert classify("과태료 부과 사전통지서 및 의견제출 안내") == "과태료"


def test_fine_collection_notice_without_advance_notice_gets_no_draft(monkeypatch):
    """의견 제출 단계가 지난 과태료(징수) 고지서엔 의견 제출서 초안을 쓰지 않는다."""
    from app import reply

    monkeypatch.setenv("LLM_API_KEY", "dummy")
    monkeypatch.setattr(
        "app.agent.extract.extract",
        lambda image, api_key: ("과태료 고지서\n과태료 금액 40,000원", []),
    )
    monkeypatch.setattr(reply, "_ask", lambda text, key: pytest.fail("초안을 쓰면 안 된다"))
    result = decode(b"fake")
    assert result.doc_type == "과태료"
    assert result.reply_draft == "" and not result.reply_needed


def test_unpaired_deadline_for_another_task_on_the_same_day_is_kept():
    """같은 날짜라도 다른 글자의 기한(의견 제출 기한 등)은 카드로 남긴다."""
    marks = [
        Mark(kind="money", text="40,000원", value="40000", bbox=[0.1, 0.30, 0.2, 0.05]),
        Mark(
            kind="deadline", text="납부기한 11.26", value="2026-11-26", bbox=[0.1, 0.31, 0.2, 0.05]
        ),
        Mark(
            kind="deadline", text="의견제출 11.26", value="2026-11-26", bbox=[0.1, 0.90, 0.2, 0.05]
        ),
    ]
    titles = [t.title for t in _todos_from_marks("과태료", marks)]
    assert titles == ["과태료 돈 내기", "과태료 내기"]
