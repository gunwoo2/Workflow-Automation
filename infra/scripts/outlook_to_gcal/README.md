# Outlook → Google Calendar 배치 동기화

> 회사 PC 한 곳에서 Outlook(COM) → JSON → Google Calendar 한 사이클로
> 실행. 추출은 PowerShell + Outlook COM (외부 API 0), 등록은 두 패턴 중
> 선택. 한 번 셋업하면 이후로는 `.\run.ps1` 한 줄.

## 두 가지 등록 패턴

| | Apps Script Web App **(default)** | OAuth Cloud Console (alt) |
|---|---|---|
| Cloud Console 가입 | ❌ 안 거침 | ✅ 거침 (결제 등록은 안 해도 OK) |
| Python 의존성 | ❌ 없음 | ✅ google-api-python-client |
| Refresh token 만료 | 없음 | 7일(Test) → publish 시 영구 |
| 인증 비밀 | shared secret 1개 | credentials.json + token.json |
| 셋업 시간 | ~5분 | ~10분 |

`run.ps1`의 default는 Apps Script. `-UseOAuth` 플래그를 주면 OAuth 패턴.

## 구성

| 파일 | 역할 |
|---|---|
| `extract_events.ps1` | Outlook COM으로 일정 + (옵션) Tasks 추출 → `events.json` |
| `register_via_appscript.ps1` | **(default)** `events.json` → Apps Script Web App POST |
| `register_to_gcal.py` | (alt) `events.json` → Google Calendar API (OAuth) |
| `run.ps1` | extract + register 한 번에 (default = Apps Script) |
| `apps_script/Code.gs` | Apps Script Web App 수신부. script.google.com에 배포 |
| `apps_script/README.md` | Apps Script 배포 절차 |
| `events.json` | 추출 결과 (gitignored — 회의 정보 포함) |
| `credentials.json` | OAuth 패턴용 (사용 시만 / gitignored) |
| `token.json` | OAuth 패턴 refresh token (자동 생성 / gitignored) |

---

## 패턴 A: Apps Script Web App (default, 권장)

### 1회 셋업 (~5분)

[`apps_script/README.md`](apps_script/README.md) 절차대로:

1. https://script.google.com → 새 프로젝트 → `Code.gs` 붙여넣기
2. `SHARED_SECRET` 32자 랜덤 문자열로 교체, 저장
3. 배포 → 웹 앱 (Execute as Me / Who has access: Anyone) → URL 복사
4. `<repo-root>/.env`에:
   ```
   GCAL_APPSCRIPT_URL=https://script.google.com/macros/s/.../exec
   GCAL_APPSCRIPT_TOKEN=<위에서 정한 SHARED_SECRET>
   ```

### 검증
```powershell
cd C:\Users\HHI\Desktop\Workflow automation\infra\scripts\outlook_to_gcal
.\run.ps1 -DaysAhead 7 -DryRun
.\run.ps1 -DaysAhead 7
```

---

## 패턴 B: OAuth Cloud Console (alt, 사용 시 `-UseOAuth`)

### 1회 셋업 (~10분)

1. https://console.cloud.google.com 새 프로젝트 (`life-os`)
   *(결제 등록 권유 화면이 떠도 무시 가능. Calendar API는 결제 활성화 안
   해도 동작.)*
2. **APIs & Services** → **Library** → "Google Calendar API" → **Enable**
3. **OAuth consent screen** → External → App 정보 입력 → Test users에 본인
   Gmail 추가 → 7일 만료 피하려면 마지막에 **Publish app** 클릭
4. **Credentials** → **Create Credentials** → **OAuth client ID** →
   Desktop app → JSON 다운로드 → `credentials.json`으로 이 디렉터리에 저장
5. ```powershell
   pip install google-auth google-auth-oauthlib google-api-python-client
   ```

### 검증
```powershell
.\run.ps1 -DaysAhead 7 -UseOAuth -DryRun
.\run.ps1 -DaysAhead 7 -UseOAuth
```

---

## 일상 운영 (양쪽 공통)

```powershell
# 향후 14일 events 동기화 (default Apps Script)
.\run.ps1

# 향후 30일
.\run.ps1 -DaysAhead 30

# Tasks도 함께 추출 (등록은 미지원, JSON에만)
.\run.ps1 -IncludeTasks

# 실제 등록 없이 추출만 시뮬레이션
.\run.ps1 -DryRun

# 다른 Google Calendar로 (OAuth 패턴만 지원)
.\run.ps1 -UseOAuth -CalendarId user@gmail.com
```

스케줄링하려면 Windows Task Scheduler:
- Trigger: 매일 08:00
- Action: PowerShell -File `<full path>\run.ps1`
- Apps Script 패턴은 첫 배포 후 무인 실행 OK
- OAuth 패턴은 첫 OAuth 셋업이 끝나면 무인 실행 OK

## Idempotency

### Apps Script 패턴
같은 (subject + start time ± 60초) 매칭으로 idempotent. 같은 분에
같은 제목 두 회의 거의 없음. 더 강한 매칭이 필요하면 OAuth 패턴
(extendedProperties 사용).

### OAuth 패턴
`outlook_entry_id`를 `extendedProperties.private`에 저장 → exact 매칭.

양쪽 모두:
- 변경 없음 → `[skip]`
- 제목/시간/장소/본문 변경됨 → `[upd ]`
- 새 이벤트 → `[new ]`

따라서 `.\run.ps1`을 **하루에 여러 번 돌려도 중복 생성 안 됨**.

## Outlook 회의 삭제 vs Google 보존

현재 동작: Outlook에서 회의가 사라져도 Google에서는 자동 삭제 안 됨.
회사 회의를 함부로 지우지 않는 환경에서는 안전한 default. 자동 삭제까지
원하면 prune 단계 추가 (다음 단계).

## 보안 주의

- `credentials.json` / `token.json` / `events.json` 모두 **gitignored**.
  절대 커밋 금지. 회의 제목·참석자 = 영업 비밀.
- Apps Script Web App URL과 `GCAL_APPSCRIPT_TOKEN`도 비밀. URL+secret이
  새는 순간 외부에서 본인 캘린더에 임의로 쓸 수 있음.
- Google Calendar는 본인 개인 계정 = 외부 클라우드. 회사 회의 정보가
  외부로 나간다는 점 인지하고 운영. 회사 NDA / DLP 정책 위반 가능성 사전
  확인 필수.
- 민감 회의는 Outlook의 **Sensitivity = Private/Confidential** 표시 →
  추출 단계에서 필터링 가능 (필요 시 알려주세요, 1줄 추가).

## 다음 단계 (지금은 미구현)

- Tasks → Google Tasks API 등록 (별도 OAuth scope 또는 Apps Script 추가)
- 양방향 동기화 (Google → Outlook)
- Life OS Inbox DB 라우팅 — 추출 결과를 노션 Inbox에도 동시 적재
- Outlook 회의 삭제 시 Google에서 prune
