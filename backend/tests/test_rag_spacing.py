from app import rag


def test_citations_allow_spaces_inside_article_number():
    # 고지서는 「제 80 조 의 2」처럼 띄어 쓰기도 한다 — 같은 조문으로 읽어야 한다
    assert rag._citations("국민건강보험법 제 80 조 의 2 에 따라") == [("국민건강보험법", "80의2")]