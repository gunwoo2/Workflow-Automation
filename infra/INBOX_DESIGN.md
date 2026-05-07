# Inbox 설계 SSoT — Life OS Phase 1+

> 모든 inbound 채널과 outbound 알람을 **단 하나의 진실** 위에 정렬한다:
> 노션 **Inbox DB**가 모든 raw 입력의 routing manifest이자 audit trail이다.
> 이 문서는 채널 카탈로그 / 봇·그룹 구조 / 알람 매트릭스 / 라우팅 규칙을
> 한 번에 정의하는 설계서다.
>
> 결정 필요 항목은 **[D-N]** 마커로 표시. 사용자가 §10 결정 큐에서 답변
> 한 번으로 디테일 전체 확정.

---

## 1. 설계 원칙

1. **단일 진실 = Inbox DB**. 모든 채널의 raw는 노션 Inbox DB에 1 row =
   1 입력. raw 텍스트가 길면(`>500자`) Hermes Episodic Archive에 두고
   `raw_archive_link`로 가리킨다.
2. **fan-out은 routed_to_***. Inbox row 1개가 Project + Task + Meeting
   여러 곳에 fan-out 가능. routed_to_* 11개 필드(Phase 1은 7개)로 표현.
3. **invariant**: 모든 Inbox row는 `pk` + `source_type` + `received_at`
   3개를 반드시 채운다. 그 외는 enrich 큐가 비동기로 채움.
4. **outbound도 같은 봇 권장**. inbound와 outbound를 같은 채널에서 보면
   "내가 시킨 것 vs 시스템이 자동으로 한 것" 구분이 자연스럽다.
5. **알람 = 사용자 시간 절도 도구**. 알람을 늘리면 자동화의 가치가 사라진다.
   하루 평균 알람 ≤ 5개를 목표 (브리핑 1 + 회의 임박 ≤ 2 + 컨펌 큐 ≤ 2).

---

## 2. 채널 카탈로그 (모든 Phase)

### 2.1 Inbound (raw → Inbox DB)

| Channel | source_type | Phase | 입력 형태 | 비고 |
|---|---|---|---|---|
| Telegram 봇 1:1 | `telegram` | **1** | text/voice/image/file | 메인 캡처 채널 |
| 노션 직접 입력 | `notion` | **1** | rich text | 데스크 앞에서 정리된 메모 |
| Cron (시스템) | `cron` | **1** | text | 스케줄·리마인더 자동 발화 |
| OneDrive watcher | `onedrive` | 2 | file | 산출물 신규/변경 감지 |
| IDE 세션 종료 훅 | `ide_session` | 2 | text | 종료 시 conversation summary |
| git commit hook | `git` | 2 | text | post-commit 메시지 |
| Outlook 메일 | `outlook` | 후순 | text/file | 프로젝트별 계정 분리 |
| Gmail | `gmail` | 후순 | text/file | 개인 메일 |
| 카톡 나의챗 | `kakao_self` | 3 | text | 폴링 봇 또는 KakaoWork |
| 음성 (Whisper) | `voice` | 3 | audio→text | 모바일 녹음 → STT |
| 웹 클립 (확장) | `web` | 3 | url+text | 브라우저 확장 |
| 수동 (Notion API) | `manual` | 1+ | any | 자동화 분류 우회용 |

### 2.2 Outbound (시스템 → 사용자)

| Alert | 트리거 | 권장 채널 | 빈도 상한 |
|---|---|---|---|
| 데일리 브리핑 | cron 매일 08:00 KST | Telegram 1:1 | 1/일 |
| 회의 임박 (15분 전) | Meeting `scheduled` 도래 | Telegram 1:1 | ≤ 5/일 |
| High Risk 발생 | Risk `priority=High` & `status=identified` | Telegram 1:1 | 즉시 |
| 컨펌 큐 도달 | Inbox `status=pending_confirm` | Telegram 1:1 (inline button) | 발생 즉시 |
| Deliverable 마감 임박 (D-3) | due_date 도래 | Telegram 1:1 | ≤ 3/일 |
| Project 단계 전환 제안 | Hermes 분석 | Telegram 1:1 | ≤ 1/주 |
| 시스템 에러 | n8n workflow 실패 | Telegram 1:1 (#error 태그) | 즉시 |

---

## 3. Telegram 봇 / 그룹 구조

### 3.1 [D-1] 봇 분할 전략 — **✅ 확정: 옵션 A** (2026-05-07)

#### 옵션 A. 봇 1개 + 1:1 chat (권장)
```
@lifeos_bot — 하나의 봇, 1:1 chat에서 모든 inbound + outbound
  inbound:  텍스트/음성/이미지/파일 → Inbox DB 'telegram' source
  outbound: 모든 알람 (#brief #meeting #risk #confirm #deadline 태그)
```
- **장점**: 가장 단순. 컨텍스트 유지(시스템 출력 옆에 사용자 답신 가능).
  KP2 Simplicity First. 알람과 inbox raw 메시지가 같은 timeline에 시간순.
- **단점**: 알람과 raw가 섞임. → 해시태그(#brief 등)로 시각 분리.
- **확장**: 나중에 반드시 분리하고 싶으면 옵션 C로 마이그레이션.

#### 옵션 B. 봇 1개 + Group with Topics (forum mode)
```
@lifeos_bot 이 다음 그룹의 멤버:
  Group "Life OS" (forum mode 활성)
    Topic 1: #inbox        (raw 입력)
    Topic 2: #brief         (데일리 브리핑)
    Topic 3: #urgent        (Risk + 컨펌 큐)
    Topic 4: #calendar      (회의 임박)
    Topic 5: #system        (n8n 에러)
```
- **장점**: 시각적으로 깔끔히 분리. 알람 종류별 mute 설정 가능.
- **단점**: 그룹 셋업 복잡, 봇이 그룹에 있어야 → 1:1 시 input route 다름.

#### 옵션 C. 봇 여러 개 (역할 분리)
```
@lifeos_inbox_bot     — raw 입력만 (silent)
@lifeos_alert_bot      — 모든 알람 (sound)
@lifeos_confirm_bot    — 컨펌 큐 전용 (sound + inline button)
```
- **장점**: 봇별 알림 설정 분리. 알람은 소리, raw는 무음.
- **단점**: 봇 3개 관리, BotFather 세팅 3번, n8n credential 3개.

**[D-1] ✅ 옵션 A 확정** — 봇 `@lifeos_bot` 1개, 1:1 chat. 알람은 hashtag로 시각 분리.

### 3.2 알람 hashtag 컨벤션 (옵션 A 채택 시)

모든 outbound 메시지 첫 줄:
```
#<category> [<priority emoji>] <짧은 제목>
<본문>
```
| 태그 | 우선순위 이모지 | 알림음 |
|---|---|---|
| `#brief` | 🟢 | silent |
| `#meeting` | 🔵 | default |
| `#risk` | 🔴 | sound |
| `#confirm` | 🟡 | default |
| `#deadline` | 🟠 | default |
| `#system` | ⚫ | sound |

Telegram의 채팅별 알림 설정으로는 봇 전체만 mute 가능. hashtag별 mute는
앱에서 안 됨 → 정 분리하고 싶으면 옵션 C.

---

## 4. 알람(outbound) 디테일

### 4.1 데일리 브리핑 — `#brief`

매일 08:00 KST cron. 다음 정보를 한 메시지로:
```
#brief 🟢 2026-05-08 (목)
━━━━━━━━━━
📅 오늘 회의 (2)
  09:30 PRJ-2026-001 Kickoff (LG화학)
  14:00 PRJ-2026-001 As-Is review
✅ 오늘 due Task (3)
  P0  PRJ-2026-001-T-0042 인터페이스 정의서 검토
  P1  PRJ-2026-001-T-0045 외화환산 시나리오
  P2  PRJ-2026-001-T-0051 단말 사전조사
🔴 활성 High Risk (1)
  PRJ-2026-001-R-005 IDoc 인코딩 (mitigating)
📥 미분류 인박스 (4) — /confirm
```

마지막 줄의 `/confirm`은 inline button 또는 슬래시 명령어.

### 4.2 회의 임박 — `#meeting`

15분 전 알람 1회:
```
#meeting 🔵 15분 후 회의
PRJ-2026-001 Kickoff
09:30~10:30 / Zoom
참석자: 김PM, 이FI리드, 박CO리드
agenda: 프로젝트 범위 / 마일스톤 / 핵심 인원 합의
[Zoom 링크 → 노션 페이지]
```

### 4.3 컨펌 큐 — `#confirm`

Inbox `status=pending_confirm` 도달 즉시:
```
#confirm 🟡 분류 컨펌 필요
IBX-20260507-0042
"내일 14시 LG화학 김PM이랑 SAP 노트 1234567 관련 회의…"
추정: OP-MEETING (0.62), inferred_project=PRJ-2026-001
[✅ 맞음] [✏️ 수정] [🗑️ Trash]
```

inline button 응답 → n8n webhook → Inbox row update + Hermes 학습 큐.

### 4.4 High Risk 발생 — `#risk`

Risk `priority=High` & `status in (identified, mitigating)` 신규:
```
#risk 🔴 High Risk 신규
PRJ-2026-001-R-007 마스터 데이터 정합성
identified · impact=High · probability=High
owner: 박CO리드
[노션 페이지]
```

### 4.5 Deliverable 마감 임박 — `#deadline`

매일 09:00 cron. due_date - today ≤ 3일 & status ∉ (approved, submitted):
```
#deadline 🟠 산출물 마감 D-2
PRJ-2026-001-D-003 화면설계서
status=drafting (target=2026-05-10)
[노션 페이지]
```

### 4.6 시스템 에러 — `#system`

n8n workflow 실패 시:
```
#system ⚫ workflow 에러
node: "Create Inbox Row" / Telegram → Notion Inbox
error: 401 Unauthorized
last input: IBX-20260507-0042 (Telegram msg 8932)
```

---

## 5. Inbox → 라우팅 매트릭스

`intent_codes` 21개 → `routed_to_*` 11개 필드 매핑. n8n 또는 Hermes SKILL이
이 표를 참조해 fan-out한다.

| intent_code | 의미 | 자동 routed_to |
|---|---|---|
| `OP-TASK` | 새 액션 항목 | `routed_to_tasks` (신규 Task create) |
| `OP-DELIV` | 산출물 관련 | `routed_to_deliverables` |
| `OP-MEETING` | 회의 관련 | `routed_to_meetings` |
| `OP-RISK` | 리스크 식별 | `routed_to_risks` |
| `OP-CALENDAR` | 일정 변경 | `routed_to_meetings` (existing) |
| `OP-PROJECT` | 새 프로젝트 | `routed_to_projects` (신규 Project — new-project SKILL trigger) |
| `OP-PROJ-UPDATE` | 프로젝트 상태 갱신 | `routed_to_projects` (existing) |
| `KN-CASE` | 케이스 자산 | (Phase 2) `routed_to_cases` |
| `KN-ERROR` | 에러 자산 | (Phase 2) `routed_to_errors` |
| `KN-RESOURCE` | 리소스 자산 | (Phase 2) `routed_to_resources` |
| `KN-TEMPLATE` | 템플릿 자산 | (Phase 2) `routed_to_templates` |
| `KN-CODE` | 코드 스니펫 | (Phase 2) `routed_to_resources` (type=스니펫) |
| `RT-SEARCH` | 검색 요청 | (no fan-out, 결과만 회신) |
| `RT-RECOMMEND` | 추천 요청 | (no fan-out) |
| `MD-COMPANY` | 회사 정보 | `routed_to_companies` |
| `MD-PERSON` | 인물 정보 | `routed_to_people` |
| `XX-MULTI` | 여러 의도 혼합 | confidence 별로 다중 routed_to_* |
| `XX-AMBIGUOUS` | 모호 | `pending_confirm` → 컨펌 큐 |
| `XX-NOTE` | 단순 메모 | (no fan-out, Inbox에만) |
| `XX-COMMAND` | 시스템 명령 | (라우팅 없음, SKILL 실행) |
| `XX-TRASH` | 폐기 | `status=trash` |

### 5.1 mentioned_* vs routed_to_*

- `mentioned_people` / `mentioned_companies` = 텍스트에 **이름이 등장**한 모든 Person/Company. 정보성.
- `routed_to_people` / `routed_to_companies` = 이 inbox가 **실질적으로 영향**을 주는 (예: 새 메일 주소 발견 → Person 업데이트). 액션성.

---

## 6. 분류 confidence + 컨펌 흐름

### 6.1 임계값

| confidence_score | 행동 |
|---|---|
| ≥ 0.85 | 자동 routed → status `routed` |
| 0.70 ~ 0.85 | 자동 routed → status `routed` (단, daily brief에 "최근 자동 분류" 요약 포함) |
| < 0.70 | status `pending_confirm` → 즉시 컨펌 큐 알람 (#confirm) |
| 분류 실패 (LLM 에러) | status `failed` → #system 알람 |

### 6.2 [D-2] 컨펌 UX — **✅ 확정: 옵션 A** (2026-05-07)

#### 옵션 A. Telegram inline button (권장)
- 즉시성: 메시지에서 바로 [✅] [✏️] [🗑️] 버튼 클릭
- 빠름. 모바일 친화. 단순 케이스 (확인/수정/폐기) 80% 커버
- 복잡한 수정(routed_to_* 직접 편집)은 노션 페이지로 jump

#### 옵션 B. 노션 컨펌 뷰
- Inbox DB의 `status=pending_confirm` 필터 뷰에서 일괄 처리
- batch 처리 효율적. 컨텍스트 풍부.
- 단점: 알람 받고 노션 열어야 함 (마찰 큼)

#### 옵션 C. 둘 다 (A=즉시, B=batch)
- 알람은 Telegram inline button으로 즉시 처리 가능
- 처리 안 한 것은 다음 데일리 브리핑에 카운트로 표시 → 노션 뷰로 batch
- 가장 유연하나 구현 복잡

**[D-2] ✅ 옵션 A 확정** — Telegram inline button (✅ / ✏️ / 🗑️). 복잡 수정은 노션 점프. 사용 패턴 보고 차후 C로 확장 검토.

### 6.3 [D-3] 자동 라우팅 보수성 — **✅ 확정: 옵션 B** (2026-05-07)

confidence ≥ 0.85여도 일부 행동은 비가역적. 어디까지 자동으로?

#### 옵션 A. 모두 자동 (가장 공격적)
- Project/Task/Meeting/Risk를 confidence ≥ 0.85면 즉시 신규 생성
- 빠르나 잘못된 row가 누적될 위험

#### 옵션 B. existing은 자동, 신규는 컨펌 (권장)
- existing entity routing(routed_to_meetings, routed_to_projects 등에
  기존 row 추가)은 자동
- **신규 Project/Risk 생성은 항상 컨펌** — 비가역에 가까움
- 신규 Task/Deliverable/Meeting 생성은 자동 (쉬운 archive 가능)

#### 옵션 C. 모두 컨펌 (가장 보수적)
- 모든 fan-out 액션을 사용자 컨펌 후 실행
- 안전하나 자동화 가치 떨어짐

**[D-3] ✅ 옵션 B 확정** — existing entity 라우팅은 자동 (`routed_to_*` 추가). 신규 Project / Risk 생성은 항상 컨펌 큐. 신규 Task / Deliverable / Meeting은 자동 (archive 비용 낮음).

---

## 7. 노션 직접 입력 채널

데스크 앞에서 사용자가 노션을 직접 열고 입력하는 케이스. 두 가지 패턴:

### 7.1 Inbox DB에 row 직접 추가 (`source_type=notion`)
- 구조화 안 된 raw 메모, 분류 미정 상태
- Hermes가 새 row를 polling(또는 노션 webhook)으로 감지 → 분류 → 라우팅
- 사용자는 일단 던지기만, 정리는 시스템이

### 7.2 Project/Task/Meeting DB에 직접 추가 (Inbox 우회)
- 사용자가 분류·구조까지 명확하게 알고 있는 케이스
- Inbox는 거치지 않음. audit trail은 노션 page history에 의존.
- 권장: **신규 Project/Risk는 직접 추가 금지** — 항상 new-project SKILL
  또는 Inbox 경유 (PK 시퀀스 보장)

### 7.3 [D-4] 노션 webhook vs polling — **✅ 확정: 옵션 B** (2026-05-07)

#### 옵션 A. Notion 공식 webhook (현재 베타)
- 노션 → n8n webhook URL 구독
- 실시간. 정확.
- 단점: 노션 webhook은 Enterprise 플랜 일부 + 베타. 제한적.

#### 옵션 B. n8n schedule + Inbox query polling (권장)
- 5분 간격 cron으로 Inbox DB query (`source_type=notion` & `status=raw` & `created_time > last_check`)
- 단순. 무료 플랜에서도 동작.
- 5분 지연 허용 가능 (인박스는 비동기 영역)

**[D-4] ✅ 옵션 B 확정** — 5분 cron polling. `infra/n8n/notion_inbox_poll.json`이 `created_time > last_check_at` 필터로 조회.

---

## 8. Cron 채널 (`source_type=cron`)

cron 자체가 Inbox에 row를 만드는 케이스 (시스템 자기-알림).

| Cron Job | 시각 | Inbox row |
|---|---|---|
| 데일리 plan 요청 | 매일 07:55 | `IBX-... source=cron name="daily-plan-trigger"` |
| 주간 회고 요청 | 금요일 17:00 | `IBX-... source=cron name="weekly-retro-trigger"` |
| 월말 자산화 큐 | 매월 마지막 평일 | (Phase 2) `KN-CASE`/`KN-RESOURCE` 큐 빌드 |
| Phase health check | 매일 22:00 | (silent) Inbox row + 통계 |

cron이 Inbox에 던지면 → Hermes가 분류 → fan-out (Task 신규 등) → 사용자가
Telegram 알람으로 받음. 같은 파이프라인 재사용.

---

## 9. 외부 ID 보존 (audit trail)

모든 Inbox row는 raw 출처를 추적 가능해야 함.

| source_type | 채워야 할 외부 ID 필드 |
|---|---|
| `telegram` | `source_account` (Telegram username), `source_message_id` (msg_id), `external_refs.telegram_chat_id` |
| `notion` | `source_url` (Notion page URL of the row), `source_account` (None) |
| `cron` | `source_message_id` (cron job name), `source_account` ("system") |
| `onedrive` | `external_refs.onedrive_item_id`, `external_refs.onedrive_path` |
| `outlook` | `external_refs.outlook_message_id`, `source_account` (account email) |
| `voice` | `voice_file` (Files), `stt_result` (Whisper output) |

source_message_id 또는 (source_type, source_account, source_message_id)
조합이 unique → **중복 방지** (같은 메시지 재처리 시 skip).

---

## 10. Phase 1 MVP vs 후순위

### Phase 1에서 구현 (지금~2주 내)
- ✅ Telegram 봇 1:1 (옵션 A 가정 시) — `infra/n8n/telegram_to_inbox.json` 준비됨
- ⏳ 노션 직접 입력 polling — `infra/n8n/notion_inbox_poll.json` (작성 예정)
- ⏳ 데일리 브리핑 cron — `infra/n8n/daily_briefing.json` (작성 예정)
- ⏳ 회의 임박 알람 — `infra/n8n/meeting_alert.json`
- ⏳ 컨펌 큐 inline button — `infra/n8n/confirm_callback.json`
- ⏳ Risk 알람 — `infra/n8n/risk_alert.json` (Risk priority Formula 변환 후)

### Phase 2 추가 (4~6주차)
- OneDrive 산출물 watcher (Microsoft Graph)
- IDE 세션 종료 훅
- git commit hook
- KN-* intent → Cases/Errors/Resources/Templates fan-out

### Phase 3+
- 카톡 / Google Calendar / Whisper / Outlook / Teams / Slack

---

## 11. 결정 큐 — 모두 확정 (2026-05-07)

| 마커 | 위치 | 확정 | 비고 |
|---|---|---|---|
| **D-1** | §3.1 봇 분할 전략 | **A** — 봇 1개 + 1:1 chat | hashtag 컨벤션(§3.2)으로 시각 분리 |
| **D-2** | §6.2 컨펌 UX | **A** — Telegram inline button | 복잡 수정은 노션 점프 |
| **D-3** | §6.3 자동 라우팅 | **B** — existing 자동, 신규 P/R 컨펌 | Task/Deliv/Meeting 신규는 자동 OK |
| **D-4** | §7.3 노션 감지 | **B** — 5분 polling | webhook은 Phase 2+ 재검토 |

### 후속 작업 (확정 결정 기반)

확정안에 맞춰 Phase 1 MVP에 필요한 n8n 워크플로우 JSON 5개를 작성한다
(사용자가 n8n 셋업 완료 후 import + 검증):

1. `infra/n8n/notion_inbox_poll.json` — D-4: 노션 직접 입력 polling
2. `infra/n8n/daily_briefing.json` — §4.1: 매일 08:00 브리핑
3. `infra/n8n/meeting_alert.json` — §4.2: 회의 15분 전 알람
4. `infra/n8n/risk_alert.json` — §4.4: High Risk 신규 알람
5. `infra/n8n/confirm_callback.json` — D-2: Telegram inline button 콜백

추가 분류·라우팅 로직(§5 매트릭스, §6.1 임계값, §6.3 신규 P/R 컨펌
하드 록)은 별도 SKILL `inbox-classify`로 분리한다 (Hermes 통합 시 단일
진입점).

---

## 12. References

- [HANDOFF.md](../HANDOFF.md) §8 채널 카탈로그 (Phase별 도입 우선순위)
- [SOUL.md](../SOUL.md) §4 Working Style, §6 Decision Rules
- [notion-db-spec.md](../notion-db-spec.md) §X1 Inbox (DB 스키마)
- [.notion/schema.py](../.notion/schema.py) Inbox 정의
- [infra/SETUP.md](SETUP.md) 인프라 셋업 절차
- [infra/n8n/telegram_to_inbox.json](n8n/telegram_to_inbox.json) Phase 1 #4 워크플로우

---

## Changelog

| 버전 | 날짜 | 변경 |
|---|---|---|
| v0.1 | 2026-05-07 | 초안 — 채널 카탈로그 / 봇 구조 / 알람 / 라우팅 / 컨펌 흐름. [D-1]~[D-4] 결정 대기. |
| v0.2 | 2026-05-07 | [D-1]=A, [D-2]=A, [D-3]=B, [D-4]=B 확정. 후속 워크플로우 JSON 5개 작업 큐 등록. |
