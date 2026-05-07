# Life OS ? Notion DB Schema (v1.0)

본 문서는 Life OS의 노션 DB 단일 진실 소스(SSoT)이다. `setup.py`가 이 명세를 기반으로
DB를 생성·갱신하며, Hermes/n8n의 라우팅 SKILL도 이 명세를 참조한다.

- **범위**: 업무 자동화 + 자산화 (재무/라이프 매니저는 Phase 4 이후 별도 추가)
- **엔티티**: 15개, 4-Tier 구조
- **핵심 원칙**: PK 불변, 익명화 게이트 OFF (실명 허용), Description으로 컨텍스트 보존
- **Phase 1 범위**: 10개 DB (Tier 0/1/2 + Inbox)
- **Phase 2 범위**: +5개 DB (Tier 0.5 + Tier 3)

---

## 목차

1. [공통 규칙](#공통-규칙)
2. [Tier 0 ? 마스터 (4개)](#tier-0--마스터)
3. [Tier 0.5 ? 마스터 이력 (1개)](#tier-05--마스터-이력)
4. [Tier 1 ? 운영 컨테이너 (1개)](#tier-1--운영-컨테이너)
5. [Tier 2 ? 운영 자식 (4개)](#tier-2--운영-자식)
6. [Tier 3 ? 자산화 (4개)](#tier-3--자산화)
7. [Tier ALL ? 인박스 (1개)](#tier-all--인박스)
8. [Relation 토폴로지](#relation-토폴로지)
9. [자동 적재 최소 필드](#자동-적재-최소-필드)
10. [Phase 1 vs Phase 2](#phase-1-vs-phase-2)
11. [빌드 가이드](#빌드-가이드)

---

## 공통 규칙

### 모든 DB가 가지는 표준 필드 (Common Fields)

| 필드명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `pk` | Title (Notion title) | ? | 불변 식별자. 노션 페이지 Title은 `pk`로 사용 (예: `PRJ-2026-001`). 검색·디버깅 효율 최우선 |
| `name` | Rich Text | ? | 사람이 읽는 이름 (예: "LG화학 차세대 ERP"). 자유 변경 가능 |
| `description` | Rich Text | ? | 긴 컨텍스트. 익명화 OFF이므로 실명/맥락 자유롭게 |
| `status` | Select | ? | 엔티티별 enum (아래 [Status Enum 표](#status-enum-표) 참조) |
| `source_inbox` | Relation → Inbox | ? | 어느 인박스 입력에서 생성됐는지 (audit trail). Inbox 엔티티 자체는 제외 |
| `external_refs` | Rich Text (JSON) | ? | 정형 외부 ID 외 기타 외부 시스템 참조용 확장 슬롯 |
| `created_time` | Created Time | (auto) | 노션 자동 |
| `updated_time` | Last Edited Time | (auto) | 노션 자동 |

> **노션 Title 필드 활용 규칙**: 노션 페이지의 Title은 `pk`(불변 코드)로 사용. 사람이 읽는 이름은 `name` 필드. 이렇게 하면 Title 변경 시에도 Relation 안 깨짐.

### PK 코드 체계 (전체)

```
Tier 0
  CO-NNNN          Company        (예: CO-0042)
  PE-NNNN          Person         (예: PE-0317)
  FI / CO / MM ... SAP Module     (표준 코드)
  BA-XXX-YYY       Business Area  (예: BA-FIN-FX)

Tier 0.5
  PCH-NNNNNN       Person-Company History (예: PCH-000123)

Tier 1
  PRJ-YYYY-NNN     Project        (예: PRJ-2026-001)

Tier 2 (Project prefix 상속)
  [Proj]-T-NNNN          Task         (예: PRJ-2026-001-T-0042)
  [Proj]-D-NNN           Deliverable  (예: PRJ-2026-001-D-012)
  [Proj]-M-YYYYMMDD-NN   Meeting      (예: PRJ-2026-001-M-20260507-01)
  [Proj]-R-NNN           Risk         (예: PRJ-2026-001-R-005)

Tier 3 (글로벌)
  CASE-YYYYMM-NNN  Case        (시계열, 예: CASE-202605-007)
  ERR-NNNNNN       Error       (글로벌 시퀀스)
  RES-NNNNNN       Resource    (글로벌 시퀀스)
  TPL-NNN          Template    (3자리)

Tier ALL
  IBX-YYYYMMDD-NNNN  Inbox     (예: IBX-20260507-0042)
```

### Status Enum 표

| 엔티티 | Status codeval (display) |
|---|---|
| Company | `active` 활성 / `inactive` 비활성 |
| Person | `active` 활성 / `inactive` 비활성 |
| SAP Module | (status 없음 ? 정적 마스터) |
| Business Area | (status 없음 ? 정적 마스터) |
| Person-Company History | `current` 현재 / `past` 과거 |
| Project | `proposed` 제안 / `active` 진행중 / `hold` 홀드 / `done` 완료 / `archived` 아카이브 |
| Task | `backlog` / `todo` / `doing` / `review` / `done` / `cancelled` |
| Deliverable | `planned` / `drafting` / `review` / `approved` / `submitted` / `obsolete` |
| Meeting | `scheduled` / `held` / `documented` / `cancelled` / `noshow` |
| Risk | `identified` / `mitigating` / `resolved` / `realized` / `closed` |
| Case | `drafted` / `validated` / `promoted` / `archived` |
| Error | `captured` / `investigating` / `solved` / `validated` / `recurring` |
| Resource | `captured` / `validated` / `battle_tested` / `deprecated` |
| Template | `drafted` / `active` / `deprecated` |
| Inbox | `raw` / `classifying` / `pending_confirm` / `routed` / `failed` / `trash` |

> **codeval 운영**: 노션 Select 옵션 이름은 한국어 자유. Hermes SKILL이 codeval ↔ 한국어 매핑 테이블 보유. 옵션 이름이 바뀌면 매핑 테이블만 수정. 옵션 자체 추가는 자유, 제거는 마이그레이션 필요.

### 외부 시스템 ID 표준 (Named Fields)

엔티티별 `external_refs` JSON 외에 자주 쓰는 named field:

```
google_calendar_id, google_event_id          (Google Calendar)
outlook_calendar_id, outlook_event_id,
outlook_account, outlook_message_id          (Outlook)
kakao_event_id, kakao_message_id             (카톡)
telegram_chat_id, telegram_message_id        (Telegram)
github_repo_url, github_commit_sha,
github_pr_url, github_issue_url              (GitHub)
onedrive_item_id, onedrive_path,
sharepoint_url                               (Microsoft 365)
slack_workspace, slack_message_ts            (Slack)
teams_workspace_id, teams_message_id         (MS Teams)
sap_note_number, sap_note_url                (SAP Notes)
```

---

## Tier 0 ? 마스터

### M1. Company (`CO-NNNN`)

회사 마스터. 한 페이지 = 한 회사. 동일 회사 중복 등록 방지를 위해 `name_hash`로 가드.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `pk` | Title | ? | `CO-NNNN` |
| `name` | Rich Text | ? | 회사명 (실명 OK) |
| `description` | Rich Text | ? | 회사 컨텍스트 |
| `status` | Select | ? | `active`/`inactive` |
| `name_hash` | Rich Text (hidden) | ? | 정규화된 실명의 SHA256 (중복 가드) |
| `aliases` | Rich Text (multi-line) | ? | 별칭 누적 (예: "엘지화학", "LG Chem") |
| `industry` | Select | ? | 제조 / 금융 / 유통 / 공공 / IT / 헬스케어 / 통신 / 에너지 / 건설 |
| `size` | Select | ? | 대기업 / 중견 / 중소 / 스타트업 / 글로벌 |
| `relationship` | Select | ? | 고객사 / 파트너 / 벤더 / 잠재 |
| `first_contact_date` | Date | ? | 첫 접점일 |
| `website` | URL | ? | |
| `industry_code` | Rich Text | ? | KSIC 등 표준 산업 분류 |
| `source_inbox` | Relation → Inbox | ? | |
| `external_refs` | Rich Text (JSON) | ? | |

**역참조** (자동): Project, Person (current_company), PCH, Case

### M2. Person (`PE-NNNN`)

인맥 마스터. 명함 OCR 통합. 동명이인은 회사+이름 조합 hash로 분리.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `pk` | Title | ? | `PE-NNNN` |
| `name` | Rich Text | ? | 이름 |
| `description` | Rich Text | ? | 인물 컨텍스트 (배경, 성향 등) |
| `status` | Select | ? | `active`/`inactive` |
| `name_hash` | Rich Text (hidden) | ? | (current_company_pk + 정규화 이름) SHA256 |
| `current_company` | Relation → Company | ? | nullable. 추후 enrich 가능 |
| `current_position` | Rich Text | ? | 직책 |
| `roles` | Multi-select | ? | PM / PO / 개발자 / 현업 / 임원 / 외주 / 기획 / QA |
| `email` | Email | ? | |
| `phone` | Phone | ? | |
| `linkedin_url` | URL | ? | |
| `business_card_image` | Files | ? | 명함 OCR 원본 |
| `first_met_date` | Date | ? | |
| `first_met_place` | Rich Text | ? | |
| `notes` | Rich Text | ? | 만남 메모 |
| `source_inbox` | Relation → Inbox | ? | |
| `external_refs` | Rich Text (JSON) | ? | |

**역참조**: Project (key_persons), Meeting (attendees), Task (assignee/reporter), Risk (owner), PCH

### M3. SAP Module (표준 코드)

SAP 모듈 표준 분류. PK = 표준 코드 자체.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `pk` | Title | ? | `FI`, `CO`, `MM`, `SD`, `PP`, `PI`, `BC`, `ABAP`, `WM`, `PS`, `QM`, `PM`, `HCM`, `Basis` 등 |
| `name` | Rich Text | ? | 한글명 (예: "재무회계") |
| `description` | Rich Text | ? | 모듈 설명 |
| `english_name` | Rich Text | ? | 영문 풀네임 (예: "Financial Accounting") |
| `category` | Select | ? | Logistics / Finance / HR / Technology / Cross |
| `skill_level` | Select | ? | Expert / Advanced / Intermediate / Novice / NoExperience |
| `aliases` | Rich Text (multi-line) | ? | S/4HANA 변경명 등 (예: HCM ↔ SuccessFactors) |
| `external_refs` | Rich Text (JSON) | ? | |

**초기 시드 (setup.py에서 일괄 등록 권장)**: FI, CO, MM, SD, PP, PI, PS, QM, PM, WM, HCM, Basis, ABAP, BW, SuccessFactors, Ariba, S4-Core, FICO (통합), SD-LE (통합)

**역참조**: Project (sap_modules), Task, Deliverable, Case, Error, Resource, Template

### M4. Business Area (`BA-XXX-YYY`)

비즈니스 영역 횡단 분류. 부모-자식 자기참조.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `pk` | Title | ? | `BA-XXX-YYY` (3자리 카테고리 + 3자리 서브) |
| `name` | Rich Text | ? | 한글명 |
| `description` | Rich Text | ? | |
| `parent_area` | Relation → Business Area (self) | ? | 상위 영역 |
| `aliases` | Rich Text (multi-line) | ? | |
| `external_refs` | Rich Text (JSON) | ? | |

**초기 시드 예시**:
- `BA-FIN-XXX`: 외화환산(FX), 매출채권(AR), 매입채무(AP), 자산회계(AA), 일반회계(GL)
- `BA-COS-XXX`: 수입부대비(IMP), 원가배부(ALC), 제품원가(PRC)
- `BA-PUR-XXX`: 일반구매(GEN), 외주구매(SUB), 자재마스터(MM)
- `BA-SAL-XXX`: 수주관리(ORD), 출하(SHP), 청구(BIL)
- `BA-PRD-XXX`: 생산계획(PLN), 작업지시(WO), BOM
- `BA-INT-XXX`: 인터페이스(IF), EDI, IDoc

**역참조**: Project, Deliverable, Case, Resource

---

## Tier 0.5 ? 마스터 이력

### M5. Person-Company History (`PCH-NNNNNN`)

사람의 회사 이력 정규화. 한 사람이 여러 회사를 거치는 경우 추적.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `pk` | Title | ? | `PCH-NNNNNN` |
| `name` | Rich Text | ? | 자동 생성: "PE-0317 @ CO-0042 (2024-2026)" |
| `description` | Rich Text | ? | |
| `status` | Select | ? | `current`/`past` |
| `person` | Relation → Person | ? | |
| `company` | Relation → Company | ? | |
| `start_date` | Date | ? | |
| `end_date` | Date | ? | null이면 현재 재직 |
| `position` | Rich Text | ? | |
| `roles` | Multi-select | ? | Person.roles와 동일 |
| `notes` | Rich Text | ? | |
| `source_inbox` | Relation → Inbox | ? | |

**규칙**: Person의 `current_company`는 status=`current`인 PCH의 company와 일치해야 함 (Hermes가 동기화 책임).

---

## Tier 1 ? 운영 컨테이너

### P0. Project (`PRJ-YYYY-NNN`)

컨설팅 프로젝트. 모든 운영 데이터의 컨테이너.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `pk` | Title | ? | `PRJ-YYYY-NNN` |
| `name` | Rich Text | ? | 프로젝트명 (예: "LG화학 차세대 ERP") |
| `description` | Rich Text | ? | 프로젝트 컨텍스트 |
| `status` | Select | ? | `proposed`/`active`/`hold`/`done`/`archived` |
| `company` | Relation → Company | ? | |
| `phase` | Select | ? | `proposal`/`analysis`/`design`/`build`/`test`/`migration`/`stabilize`/`done`/`hold` |
| `methodology` | Select | ? | Waterfall / Agile / Hybrid |
| `start_date` | Date | ? | |
| `end_planned` | Date | ? | |
| `end_actual` | Date | ? | |
| `progress_pct` | Number | ? | 0-100 |
| `my_role` | Select | ? | PM / PMO / PL / Senior / Consultant / Junior |
| `key_persons` | Relation → Person (multi) | ? | 핵심 이해관계자 |
| `sap_modules` | Relation → SAP Module (multi) | ? | |
| `business_areas` | Relation → Business Area (multi) | ? | |
| `tone_manner` | Rich Text | ? | 이 고객사 커뮤니케이션 스타일 메모 |
| **외부 시스템 ID** | | | |
| `onedrive_root_path` | Rich Text | ? | 예: `/Projects/LGChem-S4HANA/` |
| `github_repo_url` | URL | ? | |
| `google_calendar_id` | Rich Text | ? | |
| `outlook_calendar_id` | Rich Text | ? | |
| `outlook_account` | Rich Text | ? | 멀티 계정 식별 |
| `teams_workspace_id` | Rich Text | ? | |
| `slack_workspace` | Rich Text | ? | |
| `sharepoint_url` | URL | ? | |
| `external_refs` | Rich Text (JSON) | ? | |
| `source_inbox` | Relation → Inbox | ? | |

**역참조**: Task, Deliverable, Meeting, Risk, Case (출처)

---

## Tier 2 ? 운영 자식

### P1. Task (`[Proj]-T-NNNN`)

작업/이슈/액션 통합. 회의에서 도출된 액션도 여기로.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `pk` | Title | ? | `PRJ-2026-001-T-0042` |
| `name` | Rich Text | ? | 작업명 |
| `description` | Rich Text | ? | 상세 설명 |
| `status` | Select | ? | `backlog`/`todo`/`doing`/`review`/`done`/`cancelled` |
| `project` | Relation → Project | ? | |
| `task_type` | Select | ? | Task / Bug / Story / Epic / Action |
| `priority` | Select | ? | P0 / P1 / P2 / P3 |
| `assignee` | Relation → Person | ? | nullable (본인이면 비움) |
| `reporter` | Relation → Person | ? | |
| `due_date` | Date | ? | |
| `completed_date` | Date | ? | |
| `estimated_hours` | Number | ? | |
| `actual_hours` | Number | ? | |
| `sprint` | Select | ? | 자유 (예: Sprint 1, Sprint 2) |
| `parent_task` | Relation → Task (self) | ? | 상위 (Epic/Story) |
| `blocks` | Relation → Task (self, multi) | ? | 의존성 |
| `meetings` | Relation → Meeting (multi) | ? | 도출된 회의 |
| `sap_modules` | Relation → SAP Module (multi) | ? | |
| `github_issue_url` | URL | ? | |
| `github_pr_url` | URL | ? | |
| `external_refs` | Rich Text (JSON) | ? | |
| `source_inbox` | Relation → Inbox | ? | |

### P2. Deliverable (`[Proj]-D-NNN`)

단계별 산출물 메타. 실파일은 OneDrive.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `pk` | Title | ? | `PRJ-2026-001-D-012` |
| `name` | Rich Text | ? | 산출물명 (예: "To-Be 프로세스 정의서") |
| `description` | Rich Text | ? | |
| `status` | Select | ? | `planned`/`drafting`/`review`/`approved`/`submitted`/`obsolete` |
| `project` | Relation → Project | ? | |
| `phase` | Select | ? | `analysis`/`design`/`build`/`test`/`migration` |
| `deliverable_type` | Select | ? | As-Is / To-Be / IF정의서 / 화면설계서 / 단테 / 통테 / UAT / 이행계획 / 운영매뉴얼 / 교육자료 |
| `due_date` | Date | ? | |
| `submitted_date` | Date | ? | |
| `version` | Rich Text | ? | SemVer 또는 v1.0 |
| `previous_version` | Relation → Deliverable (self) | ? | 이전 버전 |
| `template_used` | Relation → Template | ? | |
| `is_milestone` | Checkbox | ? | 단계 종료 산출물 |
| `asset_extracted` | Checkbox | ? | Cases/Resources 자산화 완료 여부 |
| `sap_modules` | Relation → SAP Module (multi) | ? | |
| `business_areas` | Relation → Business Area (multi) | ? | |
| **외부 시스템 ID** | | | |
| `onedrive_item_id` | Rich Text | ? | Microsoft Graph 영구 ID |
| `onedrive_path` | Rich Text | ? | 사람이 읽는 경로 |
| `sharepoint_url` | URL | ? | |
| `file_hash` | Rich Text | ? | SHA256 (변경 감지) |
| `external_refs` | Rich Text (JSON) | ? | |
| `source_inbox` | Relation → Inbox | ? | |

### P3. Meeting (`[Proj]-M-YYYYMMDD-NN`)

회의록. `scheduled` 상태가 곧 캘린더 이벤트.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `pk` | Title | ? | `PRJ-2026-001-M-20260507-01` |
| `name` | Rich Text | ? | 회의명 |
| `description` | Rich Text | ? | |
| `status` | Select | ? | `scheduled`/`held`/`documented`/`cancelled`/`noshow` |
| `project` | Relation → Project | ? | |
| `meeting_datetime` | Date with time | ? | |
| `end_datetime` | Date with time | ? | |
| `meeting_type` | Select | ? | 정기 / 킥오프 / 리뷰 / 워크숍 / 현업IF / 세미나 / 1on1 |
| `attendees` | Relation → Person (multi) | ? | |
| `agenda` | Rich Text | ? | |
| `decisions` | Rich Text | ? | 결정사항 |
| `raw_memo` | Rich Text | ? | 텔레그램 raw |
| `structured_memo` | Rich Text | ? | Claude 구조화 결과 |
| `recording` | Files | ? | |
| `transcript` | Rich Text | ? | STT 결과 |
| `next_meeting` | Relation → Meeting (self) | ? | 후속 회의 |
| `meeting_url` | URL | ? | Zoom/Teams 링크 |
| **외부 시스템 ID** | | | |
| `google_event_id` | Rich Text | ? | |
| `outlook_event_id` | Rich Text | ? | |
| `kakao_event_id` | Rich Text | ? | |
| `external_refs` | Rich Text (JSON) | ? | |
| `source_inbox` | Relation → Inbox | ? | |

### P4. Risk (`[Proj]-R-NNN`)

프로젝트 위험요소.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `pk` | Title | ? | `PRJ-2026-001-R-005` |
| `name` | Rich Text | ? | 리스크명 |
| `description` | Rich Text | ? | |
| `status` | Select | ? | `identified`/`mitigating`/`resolved`/`realized`/`closed` |
| `project` | Relation → Project | ? | |
| `impact` | Select | ? | High / Medium / Low |
| `probability` | Select | ? | High / Medium / Low |
| `priority` | Formula | (auto) | impact × probability → High/Mid/Low |
| `response_strategy` | Select | ? | 회피 / 완화 / 전가 / 수용 |
| `response_plan` | Rich Text | ? | |
| `owner` | Relation → Person | ? | |
| `identified_date` | Date | ? | |
| `target_resolve_date` | Date | ? | |
| `realized_date` | Date | ? | 실제 발생일 (realized 시) |
| `found_in_meeting` | Relation → Meeting | ? | 발견 회의 |
| `external_refs` | Rich Text (JSON) | ? | |
| `source_inbox` | Relation → Inbox | ? | |

---

## Tier 3 ? 자산화

### K1. Case (`CASE-YYYYMM-NNN`)

고객사별 처리 사례. 익명화 OFF이므로 회사 실명 OK.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `pk` | Title | ? | `CASE-202605-007` |
| `name` | Rich Text | ? | 케이스명 (예: "수입부대비 처리 - LG화학") |
| `description` | Rich Text | ? | |
| `status` | Select | ? | `drafted`/`validated`/`promoted`/`archived` |
| `company` | Relation → Company | ? | |
| `project` | Relation → Project | ? | |
| `sap_modules` | Relation → SAP Module (multi) | ? | |
| `business_areas` | Relation → Business Area (multi) | ? | |
| `case_type` | Select | ? | 프로세스 / 커스터마이징 / 통합 / 마이그레이션 / 이행 / 인터페이스 |
| `problem_statement` | Rich Text | ? | 문제 정의 |
| `approach` | Rich Text | ? | 접근 방법 |
| `result` | Rich Text | ? | 해결 결과 |
| `reusable_pattern` | Rich Text | ? | 다음 프로젝트 적용법 |
| `source_deliverables` | Relation → Deliverable (multi) | ? | 출처 산출물 |
| `related_errors` | Relation → Error (multi) | ? | |
| `related_resources` | Relation → Resource (multi) | ? | |
| `external_refs` | Rich Text (JSON) | ? | |
| `source_inbox` | Relation → Inbox | ? | |

### K2. Error (`ERR-NNNNNN`)

오류 카탈로그.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `pk` | Title | ? | `ERR-001234` |
| `name` | Rich Text | ? | 오류명 (예: "IDoc 인코딩 오류 - inbound interface") |
| `description` | Rich Text | ? | |
| `status` | Select | ? | `captured`/`investigating`/`solved`/`validated`/`recurring` |
| `sap_modules` | Relation → SAP Module (multi) | ? | |
| `area` | Select | ? | ABAP / PI / Basis / Functional / Integration / Workflow / SmartForms |
| `error_message` | Rich Text | ? | 정확한 에러 메시지 |
| `error_code` | Rich Text | ? | |
| `symptom` | Rich Text | ? | 증상 |
| `root_cause` | Rich Text | ? | 원인 |
| `solution` | Rich Text | ? | 해결법 |
| `attempted_solutions` | Rich Text | ? | 안 됐던 시도들 |
| `frequency` | Select | ? | 자주 / 가끔 / 희귀 |
| `resolution_hours` | Number | ? | |
| `related_cases` | Relation → Case (multi) | ? | |
| `referenced_resources` | Relation → Resource (multi) | ? | |
| **외부 시스템 ID** | | | |
| `sap_note_number` | Rich Text | ? | (예: 1234567) |
| `sap_note_url` | URL | ? | |
| `github_commit_sha` | Rich Text | ? | |
| `github_pr_url` | URL | ? | |
| `external_refs` | Rich Text (JSON) | ? | |
| `source_inbox` | Relation → Inbox | ? | |

### K3. Resource (`RES-NNNNNN`)

영구 노하우 (모듈별 베스트프랙티스).

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `pk` | Title | ? | `RES-000042` |
| `name` | Rich Text | ? | 노하우명 |
| `description` | Rich Text | ? | 짧은 요약 |
| `status` | Select | ? | `captured`/`validated`/`battle_tested`/`deprecated` |
| `resource_type` | Select | ? | 노하우 / 프로세스 / 팁 / 주의사항 / 베스트프랙티스 / 체크리스트 |
| `sap_modules` | Relation → SAP Module (multi) | ? | |
| `business_areas` | Relation → Business Area (multi) | ? | |
| `area_detail` | Select | ? | Configuration / Master Data / Transaction / Reporting / Customizing / Migration |
| `body` | Rich Text | ? | 본문 |
| `source_origin` | Rich Text | ? | 출처 (본인경험 / SAP Note / 블로그 등) |
| `validation_count` | Number | ? | 적용 횟수 |
| `applied_in_cases` | Relation → Case (multi) | ? | |
| `solves_errors` | Relation → Error (multi) | ? | |
| `external_refs` | Rich Text (JSON) | ? | |
| `source_inbox` | Relation → Inbox | ? | |

### K4. Template (`TPL-NNN`)

재사용 산출물 양식. **형태(form)** 자체가 가치. 컨텐츠는 Deliverable.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `pk` | Title | ? | `TPL-018` |
| `name` | Rich Text | ? | 템플릿명 |
| `description` | Rich Text | ? | |
| `status` | Select | ? | `drafted`/`active`/`deprecated` |
| `template_type` | Select | ? | 산출물 / 회의록 / 제안서 / 계약서 / 이메일 / 보고서 |
| `target_phase` | Select | ? | (Deliverable.phase와 동일) |
| `target_deliverable_type` | Select | ? | (Deliverable.deliverable_type와 동일) |
| `sap_modules` | Relation → SAP Module (multi) | ? | |
| `form_file` | Files | ? | 빈 양식 파일 |
| `structure_notes` | Rich Text | ? | 어디를 채워야 하는지 |
| `variants_notes` | Rich Text | ? | 변형 가능 영역 |
| `source_deliverable` | Relation → Deliverable | ? | 추출 출처 |
| `usage_count` | Number | ? | 사용 횟수 (수동 또는 SKILL이 갱신) |
| `last_used_date` | Date | ? | |
| `external_refs` | Rich Text (JSON) | ? | |
| `source_inbox` | Relation → Inbox | ? | |

---

## Tier ALL ? 인박스

### X1. Inbox (`IBX-YYYYMMDD-NNNN`)

모든 raw 입력의 라우팅 매니페스트 + audit trail. **노션 인박스 = 매니페스트**, raw 풀텍스트는 짧으면 description, 길면 Hermes Episodic Archive 링크.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `pk` | Title | ? | `IBX-20260507-0042` |
| `name` | Rich Text | ? | 자동 생성: raw 첫 30자 |
| `description` | Rich Text | ? | raw 풀 (500자 미만 시 여기) |
| `status` | Select | ? | `raw`/`classifying`/`pending_confirm`/`routed`/`failed`/`trash` |
| **Source** | | | |
| `source_type` | Select | ? | telegram / notion / outlook / gmail / onedrive / ide_session / git / cron / kakao_self / voice / web / manual |
| `source_account` | Rich Text | ? | 멀티 계정 식별 (예: johndoe@lgchem.com) |
| `source_message_id` | Rich Text | ? | 채널 측 원본 ID (중복 방지) |
| `source_url` | URL | ? | 원본 위치 링크 |
| `received_at` | Date with time | ? | |
| **Attachments** | | | |
| `attachments` | Files | ? | |
| `voice_file` | Files | ? | |
| `image_file` | Files | ? | |
| `stt_result` | Rich Text | ? | 로컬 Whisper 결과 |
| `ocr_result` | Rich Text | ? | Vision OCR 결과 |
| `raw_archive_link` | URL | ? | Hermes Episodic Archive 링크 (긴 경우) |
| **Normalized** | | | |
| `normalized_text` | Rich Text | ? | 시간/사람/회사 토큰 정규화된 버전 |
| `extracted_datetimes` | Rich Text (multi-line) | ? | ISO datetime list |
| `mentioned_people` | Relation → Person (multi) | ? | 매칭된 사람 |
| `mentioned_companies` | Relation → Company (multi) | ? | |
| `raw_person_tokens` | Rich Text | ? | 매칭 안 된 이름 raw |
| `raw_company_tokens` | Rich Text | ? | |
| **Classification** | | | |
| `intent_codes` | Multi-select | ? | OP-TASK / OP-DELIV / OP-MEETING / OP-RISK / OP-CALENDAR / OP-PROJECT / OP-PROJ-UPDATE / KN-CASE / KN-ERROR / KN-RESOURCE / KN-TEMPLATE / KN-CODE / RT-SEARCH / RT-RECOMMEND / MD-COMPANY / MD-PERSON / XX-MULTI / XX-AMBIGUOUS / XX-NOTE / XX-COMMAND / XX-TRASH |
| `confidence_score` | Number | ? | 0.0~1.0 |
| `classifier` | Rich Text | ? | SKILL_NAME 또는 LLM_MODEL |
| `inferred_project` | Relation → Project | ? | 자동 추론된 활성 프로젝트 |
| `project_match_confidence` | Number | ? | |
| **Routing (Fan-out)** | | | |
| `routed_to_projects` | Relation → Project (multi) | ? | |
| `routed_to_tasks` | Relation → Task (multi) | ? | |
| `routed_to_meetings` | Relation → Meeting (multi) | ? | |
| `routed_to_risks` | Relation → Risk (multi) | ? | |
| `routed_to_deliverables` | Relation → Deliverable (multi) | ? | |
| `routed_to_cases` | Relation → Case (multi) | ? | |
| `routed_to_errors` | Relation → Error (multi) | ? | |
| `routed_to_resources` | Relation → Resource (multi) | ? | |
| `routed_to_templates` | Relation → Template (multi) | ? | |
| `routed_to_people` | Relation → Person (multi) | ? | |
| `routed_to_companies` | Relation → Company (multi) | ? | |
| **Learning** | | | |
| `user_correction` | Rich Text | ? | 사용자 정정 |
| `reprocess_count` | Number | ? | |
| `learned_into_skill` | Checkbox | ? | SKILL 학습 반영 여부 |
| `context_snapshot` | Rich Text (JSON) | ? | 처리 시점 활성 프로젝트/직전 인박스 등 |
| `external_refs` | Rich Text (JSON) | ? | |

> **노션 한계**: Inbox의 routed_to_* 11개 필드는 노션이 한 Relation 필드 = 한 DB만 지원하기 때문에 분리. 빈 Relation 비용은 0이라 부담 없음.

---

## Relation 토폴로지

### 의존성 다이어그램

```
Tier 0 마스터
  Company ←─────┐
  Person  ←──┐  │
  SAP Mod ←──┼──┤
  BizArea ←──┼──┤
             │  │
Tier 0.5    │  │
  PCH ──────┘──┘ (Person + Company 참조)

Tier 1
  Project ──→ Company / Person / SAP Module / Business Area

Tier 2 (모두 Project 참조)
  Task        ──→ Project / Person (assignee/reporter) / Task (self) / Meeting / SAP Module
  Deliverable ──→ Project / Template / Deliverable (self) / SAP Module / Business Area
  Meeting     ──→ Project / Person (attendees) / Meeting (self)
  Risk        ──→ Project / Person (owner) / Meeting

Tier 3 (글로벌, 자산)
  Case     ──→ Company / Project / SAP Module / Business Area / Deliverable / Error / Resource
  Error    ──→ SAP Module / Case / Resource
  Resource ──→ SAP Module / Business Area / Case / Error
  Template ──→ SAP Module / Deliverable

Tier ALL
  Inbox ──→ (모든 엔티티에 fan-out)
  모든 엔티티 ──→ Inbox (source_inbox)
```

### 카디널리티 매트릭스

| From → To | Cardinality | 비고 |
|---|---|---|
| Company → Project | 1 : N | 한 회사 여러 프로젝트 |
| Person → PCH → Company | 1 : N : 1 | 이력 정규화 |
| Project → Task/Deliv/Meet/Risk | 1 : N | 프로젝트 prefix로 식별 |
| Meeting ↔ Person | N : M | attendees |
| Meeting → Task | 1 : N | 회의 도출 액션 |
| Meeting → Risk | 1 : N | 회의 도출 리스크 |
| Deliverable → Template | N : 1 | 사용한 템플릿 |
| Deliverable → Case | 1 : N | 자산화 결과 |
| Case ↔ Error | N : M | 트라이앵글 1 |
| Case ↔ Resource | N : M | 트라이앵글 2 |
| Error ↔ Resource | N : M | 트라이앵글 3 |
| Task ↔ Task | N : M (self) | parent / blocks |
| Business Area ↔ Business Area | N : 1 (self) | parent |
| Inbox → 모든 엔티티 | 1 : N | fan-out |
| 모든 엔티티 → Inbox | N : 1 | source 추적 |

---

## 자동 적재 최소 필드

Hermes/n8n이 라우팅 시 어디까지 채워야 페이지 생성이 가능한지.

| 엔티티 | 최소 필수 (auto-creation) | enrich 큐로 미루는 필드 |
|---|---|---|
| Inbox | `pk`, `name`, `source_type`, `received_at`, `status=raw` | 분류·라우팅 결과 |
| Project | `pk`, `name`, `company`, `status` | phase, methodology, dates, modules |
| Task | `pk`, `name`, `project`, `status` | priority, due, assignee |
| Deliverable | `pk`, `name`, `project`, `status`, `deliverable_type` | due, version, modules |
| Meeting | `pk`, `name`, `project`, `meeting_datetime`, `status` | attendees, agenda |
| Risk | `pk`, `name`, `project`, `status`, `impact`, `probability` | response_plan, owner |
| Case | `pk`, `name`, `status` | company, modules, problem/approach/result |
| Error | `pk`, `name`, `error_message`, `status` | symptom, cause, solution |
| Resource | `pk`, `name`, `body`, `status` | modules, areas, source_origin |
| Template | `pk`, `name`, `template_type`, `status` | form_file, structure_notes |
| Company | `pk`, `name`, `name_hash`, `status` | industry, size, relationship |
| Person | `pk`, `name`, `name_hash`, `status` | company, position, contact |
| SAP Module | `pk`, `name` | category, skill_level |
| Business Area | `pk`, `name` | parent_area |
| PCH | `pk`, `person`, `company`, `start_date`, `status` | end_date, position |

> **Hermes 적재 SKILL 패턴**: 최소 필드만 채우고 status를 보수적으로 (`drafted`, `captured`, `raw`). enrich 큐가 추후 비동기로 나머지 채움.

---

## Phase 1 vs Phase 2

### Phase 1 (2~3주차) ? 10개 DB

목표: 데일리 브리핑 + Telegram 인박스 + 프로젝트 자동 셋업.

```
Tier 0 마스터 (4)
  Company, Person, SAP Module, Business Area

Tier 1 (1)
  Project

Tier 2 (4)
  Task, Deliverable, Meeting, Risk

Tier ALL (1)
  Inbox
```

**SAP Module / Business Area는 setup.py가 시드 데이터까지 일괄 등록**.

### Phase 2 (4~6주차) ? +5개 DB

목표: OneDrive 일일 학습 + 자산화 엔진 가동.

```
Tier 0.5 (1)
  Person-Company History

Tier 3 (4)
  Case, Error, Resource, Template
```

### Phase 3 이후 (제외 범위)

라이프 매니저 (개인 일정/Personal Todo/연락처 ? Person에 통합되지 않은 사적 인맥) 별도 추가.

---

## 빌드 가이드

### setup.py 동작 시나리오

1. `.env`에서 `NOTION_TOKEN`, `PARENT_PAGE_ID` 로드
2. 노션 API로 parent page 접근 가능 검증
3. 1차 생성 패스: 모든 DB 생성 (Relation 필드는 *없이*)
4. 2차 패스: Relation 필드 추가 (자기참조 / 마스터 참조 / fan-out 슬롯)
5. 3차 패스: 시드 데이터 적재 (SAP Module 19개, Business Area 카테고리 6개+서브)
6. 결과: 생성된 DB 링크 콘솔 출력 + `.notion/db_ids.json`에 ID 매핑 저장

### 멱등성 (idempotent)

- 이미 존재하는 DB는 skip (이름 매칭)
- 필드 추가는 OK, 필드 type 변경은 노션 제약 → 수동 처리 필요
- `db_ids.json`에 한 번 매핑된 ID는 보존

### 환경 분리

```
.env             (개발/실제, gitignore)
.env.example     (템플릿, 커밋)
.notion/
  db_ids.json    (노션 DB ID 매핑, gitignore)
  setup.py       (생성 스크립트)
  schema.py      (이 문서를 코드화한 단일 진실 소스)
  seed_data.py   (SAP Module / Business Area 시드)
```

### 마이그레이션 시나리오 (Mac Mini M5)

1. 새 환경에서 git pull
2. `.env` 복사 (USB 또는 1Password)
3. `python .notion/setup.py` 실행
4. 기존 노션 그대로 사용 시 → DB 이미 존재하므로 skip
5. 새 워크스페이스 시작 시 → 빈 parent page 만들고 시드 데이터까지 자동 생성

---

## 변경 이력

| 버전 | 날짜 | 변경 |
|---|---|---|
| v1.0 | 2026-05-07 | 초기 설계 ? 15 엔티티 / 4 Tier / Phase 1·2 분할 |