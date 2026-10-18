# n8n 기한 알림 — 담당: 이정관

흐름(만들 것):

1. **Webhook** — 백엔드가 해독을 마치면 `todos` 중 `due` 가 있는 것을 보낸다.
2. **Wait / Schedule** — 기한 3일 전과 당일에 깨어난다.
3. **알림** — 문자 또는 카카오 알림톡으로 「○○ 내는 날이 3일 남았어요」를 보낸다.
4. **기록** — 처리 완료를 누르면 그 할 일을 끝낸 것으로 표시한다.

만든 워크플로우는 n8n 에서 내보내기(Export)한 JSON 을 이 폴더에 `deadline-alert.json` 으로 커밋한다.
API 키·전화번호는 JSON 에 넣지 않는다 — n8n Credentials 에 둔다.

## 구현 스펙 (실제 n8n 인스턴스·전화번호 없이 미리 짠 설계 — 그대로 안 맞으면 바꿔도 됨)

### 1. 백엔드 → n8n: Webhook 호출 (아직 코드 없음, 이 부분도 새로 만들어야 함)

`backend/app/main.py`의 `decode_photo()`가 `Decoded`를 돌려주기 **직전**, `todos` 중
`due`가 있는 항목이 하나라도 있으면 n8n Webhook URL로 POST한다(실패해도 `/decode`
응답 자체는 그대로 내보낸다 — 알림 실패가 해독 실패가 되면 안 됨, `try/except`로 감싸기).

```json
POST <N8N_WEBHOOK_URL>
{
  "todo_id": "임의 생성 UUID — n8n이 기억할 키, 처리완료 콜백 때도 이 id를 씀",
  "title": "건강보험료 내기",
  "due": "2026-10-31",
  "amount": 48200,
  "how": "은행 또는 앱 납부",
  "contact": "<알림 받을 사람 연락처 — 지금은 입력 UI가 없음, 1단계는 손주모드 공유 시 입력받는 걸 제안>"
}
```

`N8N_WEBHOOK_URL`은 `backend/.env`에 새 변수로 추가(`.env.example`에도).
`todo_id`는 서버가 메모리에 들고 있지 않는다(이 서비스는 상태를 최소로 둔다는
원칙 — `backend/app/share.py` 참고) — n8n의 Wait 노드가 알아서 기억한다.

### 2. n8n 워크플로우 노드 구성

```
[Webhook 트리거] → [Wait: due - 3일까지] → [알림: "○○ 내는 날이 3일 남았어요"]
                                          → [Wait: due 당일까지] → [알림: "오늘이 ○○ 내는 날이에요"]
```

- **Wait 노드**: n8n의 `Wait` 노드는 특정 시각까지 기다릴 수 있다(`resume: "specificTime"`).
  `due`에서 3일을 빼서 Function 노드로 계산해 넣는다.
- **알림 노드**: 문자(알리고 등 SMS API)나 카카오 알림톡 중 하나 — 어느 쪽이든 n8n
  HTTP Request 노드 + Credentials로 처리(키는 노드 밖 Credentials에만).
- **메시지 템플릿**: `쉬운말 가이드`(`docs/06-쉬운말-가이드.md`) 기준 — "{title} 내는 날이
  {N}일 남았어요. {amount}원, {how}." 형태로, 한자어 없이 40자 이내.
- **처리 완료 콜백**: 사용자가 "처리 완료" 버튼을 누르면(화면 쪽은 아직 없음 — 이것도
  FR-08 범위) `POST /webhook/<n8n-id>/done` 같은 별도 Webhook으로 n8n에 알려서,
  그 `todo_id`의 남은 Wait를 취소한다(n8n `Respond to Webhook` 또는 워크플로우
  중단용 두 번째 트리거로 구성).

### 3. 테스트 방법 (실제 전화번호 없이)

n8n Webhook 노드의 테스트 URL로 위 JSON을 `curl -X POST`로 직접 보내보고, Wait
노드 타이밍이 의도대로 걸리는지 n8n 실행 로그로 확인한다. 알림 발송 노드만
"실행 안 함(Deactivate)"으로 꺼두면 실제 문자 발송 없이 흐름 검증이 가능하다.
