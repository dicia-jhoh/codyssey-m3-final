"""샘플 모드에서 돌려줄 해독 결과 — 가짜 공문 1건이다(실제 고지서가 아님).

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
        Basis(
            claim="기한을 넘기면 돈을 조금 더 내야 해요.",
            quote="납부기한이 지나면 연체금이 부과됩니다.",
            law="국민건강보험법 제80조",
        )
    ],
    sample=True,
)
