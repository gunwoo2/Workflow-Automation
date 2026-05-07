# Life OS ? Handoff (Web → Local VSCode)

이 문서는 Claude Code on the Web 세션에서 진행한 설계 작업을 로컬 VSCode + Claude Code로
이관하기 위한 컨텍스트 핸드오프이다. 새 세션에서 이 문서를 읽으면 바로 이어 작업 가능하다.

## TL;DR

- **목표**: SAP 컨설턴트 1인용 Life OS 시스템 구축 (PMO 자동화 + 지식 자산화)
- **진행 상태**: 노션 DB 설계 완료 (15 엔티티, 4 Tier). 빌드 직전에 web 샌드박스의 외부 호출
  차단으로 중단
- **다음 작업**: 로컬에서 `setup.py` 빌드 후 노션에 10개 DB 일괄 생성 (Phase 1 범위)

---

## 1. 작업 진행 흐름 (어디까지 했나)

### 완료
1. 원본 설계서 (`Life_OS_Final_Design.pdf`) 학습 ? 48페이지
2. **목적 재정의**: 업무 자동화 + 자산화로 범위 압축 (재무/라이프 매니저는 Phase 4 이후)
3. **인박스 채널 카탈로그**: 8 카테고리 약 20개 채널 정리 + 프로젝트별 가변 채널 매핑 방식
4. **OpenClaw vs Hermes vs 노션 인박스 역할 분리**:
   - OpenClaw = 채널 게이트웨이 (분류 안 함)
   - Hermes = 두뇌 + 평생 기억 (raw는 SQLite Episodic Archive)
   - 노션 인박스 = 라우팅 매니페스트 + audit trail
5. **데이터 엔티티 도출**: 15개 (Tier 0/0.5/1/2/3/ALL)
6. **키 설계 라운드 1**: PK 코드 체계 확정
7. **키 설계 라운드 2**: 외부 ID 슬롯, Status enum, 마스터 unique, 자기참조/fan-out
8. **`notion-db-spec.md` (729줄) 작성** ? 단일 진실 소스 (SSoT)

### 미완료 (환경 제약으로 중단)
- `.notion/setup.py` (DB 일괄 생성 스크립트)
- `.notion/seed_data.py` (SAP Module 19개 + Business Area 30개+)
- 노션 DB 실제 생성

### 환경 차단 이슈
- **api.notion.com 차단**: web 샌드박스 allowlist 미포함 → 직접 API 호출 불가
- **git push 차단**: 프록시 자격증명 read-only → 로컬 커밋만 누적 (1개 미푸시)
- 로컬 VSCode + Claude Code 데스크톱 앱에서는 둘 다 해결됨

---

## 2. 핵심 설계 결정 (절대 까먹으면 안 됨)

### 2.1 범위 결정
- **포함**: PMO 자동화 (프로젝트/작업/회의/리스크/산출물) + 자산화 (Cases/Errors/Resources/Templates)
- **제외 (Phase 4+)**: 재무 시스템, 라이프 매니저 (개인 일정/할일/연락처)
- **익명화 게이트**: OFF (실명 자유 사용 ? 사용자 결정)

### 2.2 키 설계 ? A안 모두 채택
- **KD1**: Project 코드에 회사 정보 안 박음 (`PRJ-2026-001`) → 회사 변경 무영향
- **KD2**: Tier 2 자식은 Project prefix 상속 (`PRJ-2026-001-T-0042`)
- **KD3**: Cases는 시계열 PK (`CASE-202605-007`) → 5년 누적 시 검색 효율
- **KD4**: SAP Module은 표준 코드 그대로 PK (`FI`, `CO`) + aliases 슬롯
- **KD5**: enum codeval은 영문 snake_case + Hermes 매핑 테이블
- **KD6**: 모든 엔티티에 `external_refs` JSON 슬롯 (확장성)
- **KD7**: Inbox routed_to_* 11개 분리 필드 (노션 한계 우회)
- **KD8**: file_hash로 산출물 변경 감지 (Microsoft Graph etag와 별개)
- **KD9**: Person.current_company nullable (추후 enrich)

### 2.3 표준 필드 트리오 (모든 엔티티)
- `pk` ? Notion Title (불변)
- `name` ? 사람이 읽는 이름 (자유 변경)
- `description` ? 긴 컨텍스트

### 2.4 PK 체계 요약
```
CO-NNNN          Company        PE-NNNN          Person
FI/CO/MM/...     SAP Module     BA-XXX-YYY       Business Area
PCH-NNNNNN       Person-Company History
PRJ-YYYY-NNN     Project
[Proj]-T-NNNN    Task           [Proj]-D-NNN     Deliverable
[Proj]-M-YYYYMMDD-NN  Meeting   [Proj]-R-NNN     Risk
CASE-YYYYMM-NNN  Case           ERR-NNNNNN       Error
RES-NNNNNN       Resource       TPL-NNN          Template
IBX-YYYYMMDD-NNNN  Inbox
```

### 2.5 Phase 1 vs Phase 2 분할
- **Phase 1 (10 DB)**: 마스터 4 + Project + Tier 2 4개 + Inbox
- **Phase 2 (+5 DB)**: PCH + Tier 3 4개 (Cases/Errors/Resources/Templates)

### 2.6 시드 데이터 (setup.py가 일괄 등록)
- **SAP Module 19개**: FI, CO, MM, SD, PP, PI, PS, QM, PM, WM, HCM, Basis, ABAP, BW,
  SuccessFactors, Ariba, S4-Core, FICO (통합), SD-LE (통합)
- **Business Area 카테고리 6 + 서브 다수**:
  - `BA-FIN-XXX`: 외화환산(FX), 매출채권(AR), 매입채무(AP), 자산회계(AA), 일반회계(GL)
  - `BA-COS-XXX`: 수입부대비(IMP), 원가배부(ALC), 제품원가(PRC)
  - `BA-PUR-XXX`: 일반구매(GEN), 외주구매(SUB), 자재마스터(MM)
  - `BA-SAL-XXX`: 수주관리(ORD), 출하(SHP), 청구(BIL)
  - `BA-PRD-XXX`: 생산계획(PLN), 작업지시(WO), BOM
  - `BA-INT-XXX`: 인터페이스(IF), EDI, IDoc

---

## 3. 레포 현재 상태

### 파일
```
/home/user/Workflow-Automation/
├── Life_OS_Final_Design.pdf   ← 원본 설계서 (48p)
├── Life_OS_Final_Design.docx  ← 원본 (동일 내용)
├── notion-db-spec.md          ← ★ 단일 진실 소스 (729줄)
└── HANDOFF.md                 ← 이 문서
```

### 브랜치
- 작업 브랜치: `claude/explore-repository-xSn4Q`
- 푸시 안 된 커밋: `49c64e5 Add notion-db-spec.md (15 entities, 4-tier schema)`
- 원격에 있는 브랜치: `add-life-os-design` (PDF/docx만)

### 푸시 방법
로컬 VSCode에서 받아서 그냥 `git push` 하면 됨. Claude Code 데스크톱 앱 / 일반 git 클라이언트
모두 작동.

---

## 4. 보안 - 노션 토큰 관리

Notion Integration Token은 로컬 환경의 안전한 보관소(1Password, .env 등)에서만 관리하세요. 공개된 채팅/리포지토리에는 절대 토큰을 노출하지 마세요. 노출된 토큰은 즉시 https://www.notion.so/profile/integrations 에서 로테이트해야 합니다.

페이지 ID는 공개돼도 무방 (token 없으면 무력):
```
PARENT_PAGE_ID = 3597221afa4880ce8305cbe42a7468ff
PARENT_PAGE_URL = https://www.notion.so/Life-OS-3597221afa4880ce8305cbe42a7468ff
```

---

## 5. 로컬 VSCode에서 이어할 작업 (다음 세션 프롬프트 추천)

### 첫 메시지 추천
```
이 레포 HANDOFF.md 와 notion-db-spec.md 읽고 컨텍스트 파악해줘.

다음 작업: Phase 1 노션 DB 10개 자동 생성 스크립트 작성.

요구사항:
- Python stdlib만 사용 (urllib + json) ? pip 의존성 없음
- 멱등 (재실행 시 기존 DB skip)
- 2-pass: (1) 모든 DB 생성 (relation 제외) → (2) relation 추가
- 3-pass: 시드 데이터 적재 (SAP Module 19 + Business Area 30+)
- .env에서 NOTION_TOKEN, PARENT_PAGE_ID 로드
- .gitignore에 .env, .notion/db_ids.json 추가
- .env.example 템플릿 커밋

파일 구조:
.notion/
  setup.py        ? 메인 스크립트
  schema.py       ? DB 스키마 정의 (notion-db-spec.md 코드화)
  seed_data.py    ? 시드 데이터
  README.md       ? 실행 방법

작업 후 노션 토큰 새로 받아서 setup.py 실행하고 결과 검증.
```

### 사전 준비 (사용자)
1. 노션 토큰 로테이트 (위 4번)
2. 새 토큰을 `.env`에 저장:
   ```
   NOTION_TOKEN=새_토큰
   PARENT_PAGE_ID=3597221afa4880ce8305cbe42a7468ff
   ```
3. Python 3.10+ 설치 확인 (`python --version` 또는 `py --version`)

### 실행 절차 (Claude가 코드 작성 후)
```powershell
# Windows PowerShell
cd C:\path\to\Workflow-Automation
python .notion\setup.py
```
- 출력: 생성된 10개 DB 링크 + `.notion/db_ids.json`에 ID 매핑
- 노션에서 "Life OS" 페이지 열어보면 DB들이 자식으로 생성됨

### 검증 체크리스트
- [ ] 10개 DB 모두 생성 (Company, Person, SAP Module, Business Area, Project, Task,
  Deliverable, Meeting, Risk, Inbox)
- [ ] SAP Module DB에 19개 row 시드됨
- [ ] Business Area DB에 30개+ row 시드됨 (parent_area 계층 동작)
- [ ] Project DB에서 Task/Deliverable/Meeting/Risk 4개 Relation 정상 동작
- [ ] Inbox DB에 routed_to_* 11개 Relation 필드 모두 표시
- [ ] Person DB에 current_company Relation → Company 연결됨

---

## 6. 12주 로드맵 위치

```
[Phase 0] 기반 (1주)
[Phase 1] PMO MVP (2~3주차)  ← ★ 노션 DB 빌드는 여기 시작점
[Phase 2] 지식 자산화 (4~6주차)
[Phase 3] 라이프 매니저 (7~8주차)
[Phase 4] CFO + 대시보드 (9~10주차)
[Phase 5] AI 세무사 (11~12주차)
```

### Phase 0 미완 항목 (병행 가능)
- WSL2 + Docker Desktop 설치 (M5 오면 안 해도 됨)
- Telegram Bot 생성 (BotFather)
- Notion 통합 생성 ? (했음)
- GitHub PAT 발급
- Google Calendar API 키
- Whisper 로컬 설치

### Phase 1 작업 순서 (이 핸드오프 후)
1. **노션 DB 빌드** (이 세션에서 다음에 할 일)
2. SOUL.md 페르소나 + 카파시 4원칙 작성
3. ~/.claude/CLAUDE.md 글로벌 설정
4. Telegram → 노션 인박스 워크플로우 (n8n)
5. 데일리 브리핑 cron (n8n)
6. "새프로젝트 X" 자동 셋업 SKILL

---

## 7. 미해결 의사결정 (다음 세션에서 결정)

이전 라운드에서 합의한 의사결정 외에 아직 안 정한 것들:

### D1. Person-Company History의 데이터 입력 시점
- A. 첫 등록 시 무조건 PCH도 같이 생성 (2개 페이지)
- B. PCH는 이직 발생 시에만 생성 (회사 안 바뀌면 PCH 0개)
- B안이 단순. Hermes가 Person.current_company 변경 감지 시 자동 PCH 생성

### D2. 노션 인박스에 raw 텍스트 길이 제한
- 합의: <500자 = description에 저장 / ≥500자 = Hermes Episodic Archive 링크
- 미정: 정확히 description 한도가 노션 API에서 얼마인지 (2000자가 한 block 한도)
- setup.py 작성 시점에 확인 필요

### D3. Calendar는 Meeting DB로 통합 vs 별도
- 합의: Meeting의 `scheduled` 상태가 곧 캘린더 이벤트
- 미정: 회의 아닌 단순 일정 (개인 약속, 마감일)은 어떻게? Phase 3 라이프 매니저까지 보류

### D4. Hermes SKILL 매핑 테이블 위치
- enum codeval ↔ 한국어 라벨 매핑이 필요
- 옵션: SKILL.md 내부 / 별도 yaml / Notion DB 자체에서 추출
- 추후 Hermes 셋업 시 결정

---

## 8. 참고 ? 채널 카탈로그 (Phase 1 → Phase 후순)

설계 시점 합의된 인박스 채널 우선순위:

| Phase | 도입 채널 |
|---|---|
| **Phase 0~1** | Telegram + 노션 직접 + Cron |
| Phase 2 | OneDrive + IDE 세션 + git commit |
| Phase 3 | 카톡 나의챗 + Google Calendar 양방향 + 음성/이미지 |
| Phase 후속 | Outlook (프로젝트별) + Teams + Slack |

프로젝트별 가변 채널 (Outlook/Teams 등)은 **Project DB의 외부 ID 필드**에 매핑 정보 저장:
- `outlook_account`, `outlook_calendar_id`, `teams_workspace_id`, `slack_workspace`,
  `sharepoint_url` 등 9개 named field + `external_refs` JSON

---

## 9. 핵심 참조 문서

- `notion-db-spec.md` ? DB 스키마 단일 진실 소스 (시작점)
- `Life_OS_Final_Design.pdf` ? 원본 설계서 (48페이지)

이 두 개만 읽으면 컨텍스트 100% 복원 가능.