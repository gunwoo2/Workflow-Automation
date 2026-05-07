# Outlook → Google Calendar 배치 동기화

> 회사 PC 한 곳에서 Outlook(COM) → JSON → Google Calendar 한 사이클로
> 실행. 추출은 PowerShell + Outlook COM (외부 API 0), 등록만 Python +
> Google Calendar API. 한 번 셋업하면 이후로는 `.\run.ps1` 한 줄.

## 구성

| 파일 | 역할 |
|---|---|
| `extract_events.ps1` | Outlook COM으로 일정 + (옵션) Tasks 추출 → `events.json` |
| `register_to_gcal.py` | `events.json` → Google Calendar (idempotent upsert) |
| `run.ps1` | 위 둘을 한 번에 실행 |
| `credentials.json` | Google OAuth client (사용자 셋업, gitignored) |
| `token.json` | refresh token 캐시 (자동 생성, gitignored) |
| `events.json` | 추출 결과 (gitignored — 회의 정보 포함) |

## 1회 셋업 (~10분)

### 1. Google Cloud OAuth client 생성

1. https://console.cloud.google.com 접속 → 새 프로젝트 (예: `life-os`)
2. 좌측 메뉴 → **APIs & Services** → **Library**
3. "Google Calendar API" 검색 → **Enable**
4. 좌측 메뉴 → **APIs & Services** → **OAuth consent screen**
   - User Type: **External** 선택 → Create
   - App name: `Life OS Calendar Sync`, support email: 본인 이메일
   - Scopes: 그대로 Save and Continue
   - Test users: 본인 Gmail 주소 추가 → Save and Continue
5. 좌측 메뉴 → **APIs & Services** → **Credentials**
   - **Create Credentials** → **OAuth client ID**
   - Application type: **Desktop app**
   - Name: `Life OS Desktop` → Create
6. 다운로드 버튼 (⬇️) 으로 JSON 받기 → 이 파일을 `credentials.json`으로
   이 디렉터리에 저장

### 2. Python 라이브러리 설치

```powershell
pip install google-auth google-auth-oauthlib google-api-python-client
```

회사 PC에서 pip이 차단됐다면:
- 회사 IT에 "Python google-api-python-client 설치 가능?" 확인, 또는
- 본인 PC에서 wheel 받아서 USB로 옮기기 (`pip download` + `pip install --no-index`)

### 3. 첫 실행 (OAuth 동의)

```powershell
.\run.ps1 -DaysAhead 7 -DryRun
```

`-DryRun`은 Google API 호출 없이 추출만 시뮬레이션 — 추출 데이터 모양
확인용. 출력에 events 리스트가 잘 보이면 진짜 실행:

```powershell
.\run.ps1 -DaysAhead 7
```

첫 실행 시 register 단계에서 **브라우저가 열림** → 본인 Google 계정 선택
→ "이 앱은 Google에서 검증되지 않았습니다" 경고 → **Advanced** → **Go to
Life OS Calendar Sync (unsafe)** → 권한 동의 → 완료. `token.json`이 자동
생성되며 이후 실행은 비대화식.

### 4. 검증

Google Calendar 웹에서 추가된 이벤트 확인. 각 이벤트의 상세 보기에서
`extendedProperties.private.outlook_entry_id`가 채워져 있으면 OK
(idempotent matching에 사용됨).

## 일상 운영

매일 또는 매주 한 번 실행:

```powershell
# 향후 14일 events 동기화 (default)
.\run.ps1

# 향후 30일
.\run.ps1 -DaysAhead 30

# Tasks도 함께 추출 (등록은 미지원, JSON에만)
.\run.ps1 -IncludeTasks

# 다른 Google Calendar로 등록
.\run.ps1 -CalendarId user@gmail.com
```

스케줄링하려면 Windows Task Scheduler:
- Trigger: 매일 08:00
- Action: PowerShell -File `<full path>\run.ps1`
- 첫 OAuth 셋업이 끝났으면 무인 실행 OK

## Idempotency

- 같은 `outlook_entry_id`를 가진 이벤트가 이미 Google에 있으면:
  - 변경 없음 → `[skip]`
  - 제목/시간/장소/본문 변경됨 → `[upd ]` (insert 아닌 update)
- 새로운 이벤트 → `[new ]`

따라서 `.\run.ps1`을 **하루에 여러 번 돌려도 중복 생성 안 됨**.

## Outlook 회의 삭제 vs Google 보존

현재 동작: Outlook에서 회의가 사라져도 Google에서는 자동 삭제 안 됨
(추출 결과에 빠져있을 뿐, 등록 측이 해당 entry_id를 안 봐서). 회사 회의를
함부로 지우지 않는 환경에서는 안전한 default. 자동 삭제까지 원하면
`register_to_gcal.py`에 prune 단계 추가 (다음 단계에서 작업).

## 보안 주의

- `credentials.json` / `token.json` / `events.json` 모두 **gitignored**.
  절대 커밋 금지. 회의 제목·참석자 = 영업 비밀.
- Google Calendar는 본인 개인 계정 = 외부 클라우드. 회사 회의 정보가
  외부로 나간다는 점 인지하고 운영. 회사 NDA / DLP 정책 위반 가능성 사전
  확인 필수.
- 민감 회의는 Outlook의 **Sensitivity = Private/Confidential** 표시 →
  추출 단계에서 필터링 가능 (필요 시 알려주세요, 1줄 추가).

## 다음 단계 (지금은 미구현)

- Tasks → Google Tasks API 등록 (별도 OAuth scope 필요)
- 양방향 동기화 (Google → Outlook)
- Life OS Inbox DB 라우팅 — 추출 결과를 노션 Inbox에도 동시 적재
- Outlook 회의 삭제 시 Google에서 prune
