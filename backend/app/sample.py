"""샘플 모드에서 돌려줄 해독 결과 — 가짜 고지서 1건이다(실제 고지서가 아님).

LLM 키가 없어도 화면·n8n 을 끝까지 시험할 수 있게 한다.
"""

from .schema import Basis, Decoded, Mark, Todo

SAMPLE = Decoded(
    doc_type="고지서",
    title="[샘플] 2026년 10월분 건강보험료 납부 안내",
    plain=[
        "10월 건강보험료 48,200원을 내야 해요.",
        "10월 31일까지 내면 돼요.",
        "기한을 넘기면 돈을 조금 더 내야 해요(연체금).",
    ],
    marks=[
        Mark(kind="money", text="48,200원", value="48200", bbox=[0.55, 0.32, 0.25, 0.05]),
        Mark(kind="deadline", text="2026. 10. 31.", value="2026-10-31", bbox=[0.55, 0.40, 0.25, 0.05]),
        Mark(kind="document", text="납부서(뒷면)", value="납부서", bbox=[0.10, 0.85, 0.30, 0.05]),
    ],
    todos=[Todo(title="건강보험료 내기", due="2026-10-31", amount=48200, how="은행 또는 앱 납부")],
    basis=[
        # quote는 실제 조문 원문(law.go.kr 조문정보, 시행 2026-10-08) — data/legal/articles.jsonl과
        # 같은 문장. 샘플이라고 근거까지 지어내면 "AI 풀이 — 원문을 함께 확인하세요" 배지가 거짓이 된다.
        Basis(
            claim="기한을 넘기면 돈을 조금 더 내야 해요.",
            quote="공단은 보험료등의 납부의무자가 납부기한까지 보험료등을 내지 아니하면 그 납부기한이 지난 날부터 매 1일이 경과할 때마다 다음 각 호에 해당하는 연체금을 징수한다.",
            law="국민건강보험법 제80조",
        )
    ],
    sample=True,
)
