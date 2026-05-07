# Phase 0 인프라 셋업

> Phase 1 자동화(Telegram → 노션 인박스 / 데일리 브리핑 cron)를 돌리려면
> 외부 인프라 셋업이 필요하다. 모두 1회성이며, 셋업 후 `.env`에 토큰만
> 채우면 모든 워크플로우가 동작한다.

## 0. 체크리스트

- [ ] Telegram Bot 생성 (BotFather)
- [ ] 본인 Telegram Chat ID 확인
- [ ] n8n 설치 (Docker 또는 클라우드)
- [ ] n8n에서 Notion 자격증명 등록
- [ ] n8n에 [`infra/n8n/telegram_to_inbox.json`](n8n/telegram_to_inbox.json) 임포트
- [ ] 인박스 → 노션 라우트 1회 검증

---

## 1. Telegram Bot 생성

1. Telegram에서 `@BotFather` 검색 → 대화 시작
2. `/newbot` 입력
3. 봇 이름 (예: `Life OS Inbox`) 입력
4. 봇 username (예: `lifeos_inbox_bot`) 입력 — `_bot`으로 끝나야 함
5. 받은 **HTTP API token**을 `.env`에 추가:
   ```
   TELEGRAM_BOT_TOKEN=1234567890:AAH...
   ```
6. 본인의 **Chat ID** 확인:
   - 방금 만든 봇 검색 → 대화 시작 → `/start` 또는 아무 메시지 보내기
   - 브라우저에서 열기:
     `https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getUpdates`
   - JSON 응답의 `result[0].message.chat.id` 값이 본인 Chat ID
   - `.env`에 추가:
     ```
     TELEGRAM_CHAT_ID=123456789
     ```

> 봇은 **소유자(본인)와 1:1 채팅**만 처리한다. 다른 사용자가 메시지를 보내도
> n8n 워크플로우의 `chat_id == TELEGRAM_CHAT_ID` 필터로 거른다.

---

## 2. n8n 설치

### 옵션 A — Docker Desktop (권장, 로컬)

```powershell
# Windows PowerShell — 작업 디렉터리에서
docker run -d --restart unless-stopped `
  --name n8n `
  -p 5678:5678 `
  -v n8n_data:/home/node/.n8n `
  -e GENERIC_TIMEZONE=Asia/Seoul `
  -e TZ=Asia/Seoul `
  -e N8N_SECURE_COOKIE=false `
  docker.n8n.io/n8nio/n8n:latest
```

브라우저에서 `http://localhost:5678` 열면 첫 실행 시 계정 생성 화면.

### 옵션 B — n8n Cloud

`https://n8n.cloud` 가입 → starter plan 시작. URL은 `https://<your-instance>.app.n8n.cloud`.

### 옵션 C — Mac mini M5 도착 후

같은 docker 명령. M5에서 동일하게 동작 (ARM64 이미지 자동 선택).

---

## 3. n8n에 Notion 자격증명 등록

1. n8n 좌측 메뉴 → **Credentials** → **Add Credential** → **Notion API**
2. **Internal Integration Token** 필드에 `.env`의 `NOTION_TOKEN` 값 붙여넣기
3. Save → Test 통과 확인

> **주의**: 노션 통합이 **Inbox DB의 부모 페이지**(또는 Inbox DB 자체)에
> 공유돼 있어야 함. `.notion/setup.py`로 빌드했다면 부모 페이지에 이미
> 공유된 상태.

---

## 4. 워크플로우 임포트

1. n8n 좌측 메뉴 → **Workflows** → **Import from File**
2. [`infra/n8n/telegram_to_inbox.json`](n8n/telegram_to_inbox.json) 선택
3. 임포트된 워크플로우 열기 → 각 노드의 자격증명 / 환경변수 설정:
   - **Telegram Trigger** 노드: `TELEGRAM_BOT_TOKEN` 자격증명 등록
   - **Notion Create Page** 노드: `NOTION_TOKEN` 자격증명 등록
   - **Notion DB ID**: `.notion/db_ids.json`의 `inbox` 값으로 교체
4. 우측 상단 **Active** 토글 ON

---

## 5. 검증 (KP4 Goal-Driven Execution)

성공 기준:
- [ ] Telegram 봇에 텍스트 메시지 전송 (예: "테스트 인박스")
- [ ] 5초 이내 Notion **Inbox** DB에 새 row 등장
- [ ] Row의 `pk` = `IBX-YYYYMMDD-NNNN`, `name` = 메시지 첫 30자
- [ ] `description` = raw 메시지 전문, `status` = `raw`
- [ ] `source_type` = `telegram`, `source_message_id` = Telegram 메시지 ID
- [ ] `received_at` = 메시지 수신 시각

전부 ✅이면 Phase 1 #4 완료. 다음 단계(#5 데일리 브리핑 cron) 진입.

---

## 6. 후속 채널 (Phase 2 이후)

| 채널 | Phase | 셋업 트리거 |
|---|---|---|
| OneDrive (산출물 자동 import) | 2 | Microsoft Graph API key 발급 |
| IDE 세션 / git commit | 2 | GitHub PAT (이미 발급?) |
| 카톡 나의챗 | 3 | 별도 폴링 봇 또는 KakaoWork API |
| Google Calendar 양방향 | 3 | Google Cloud project + OAuth |
| 음성 / 이미지 / Whisper | 3 | 로컬 Whisper 설치 + 파일 업로드 트리거 |
| Outlook (프로젝트별) | 후순 | Microsoft 365 OAuth |
| Teams / Slack | 후순 | 워크스페이스별 봇 |

각 채널 도입 시점에 별도 n8n 워크플로우를 추가한다. 모두 종착점은 동일:
**노션 Inbox DB row 생성**.
