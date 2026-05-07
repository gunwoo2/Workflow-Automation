# Apps Script Web App 배포 (~5분, 1회)

> Cloud Console·OAuth client·결제 등록 모두 우회. script.google.com에서
> 직접 시작 → Web App URL + shared secret만 PowerShell에 등록하면 끝.

## 1. 새 Apps Script 프로젝트

1. https://script.google.com 접속 (본인 Google 계정)
2. 좌측 상단 **새 프로젝트**
3. 프로젝트 이름: `Life OS Outlook Sync`
4. 기본 `Code.gs` 내용을 모두 지우고, 이 디렉터리의 [`Code.gs`](Code.gs)
   내용을 그대로 복사·붙여넣기
5. 상단의 두 상수 교체:
   - `SHARED_SECRET` — 32자 이상 랜덤 문자열 (예: `openssl rand -hex 32`
     또는 1Password 생성기). 이걸 PowerShell `.env`에도 같은 값으로 넣음.
   - `CAL_ID` — `primary` 그대로 두면 본인 기본 캘린더. 다른 캘린더면
     캘린더 ID (Google Calendar 설정 → "캘린더 통합" → 캘린더 ID)
6. 💾 저장 (Ctrl+S)

## 2. 배포

1. 우측 상단 **배포** → **새 배포**
2. ⚙️ 톱니바퀴 → **웹 앱** 선택
3. 설정:
   - **설명**: `v1` (다음에 바꾸면 v2…)
   - **다음 사용자로 실행**: **나** (본인 권한으로 캘린더 접근)
   - **액세스 권한이 있는 사용자**: **모든 사용자**
     - "구글 계정 보유자"가 아닌 그냥 "모든 사용자"여야 PowerShell이
       OAuth 없이 호출 가능. shared secret으로 보호됨.
4. **배포** 클릭
5. 처음에는 권한 동의 팝업:
   - "검토되지 않음 / Google에서 확인하지 않음" 경고 → **고급** → **Life
     OS Outlook Sync(으)로 이동(안전하지 않음)** → **허용**
6. 배포 완료 화면에서 **웹 앱 URL** 복사 (형식:
   `https://script.google.com/macros/s/AKfycbz.../exec`)

## 3. PowerShell 환경 변수에 등록

`<repo-root>/.env` 또는 시스템 환경 변수에 추가:

```
GCAL_APPSCRIPT_URL=https://script.google.com/macros/s/AKfycbz.../exec
GCAL_APPSCRIPT_TOKEN=<2번에서_정한_SHARED_SECRET>
```

## 4. 검증 (3단계)

### 4-1. GET (헬스 체크)
브라우저에서 위 URL을 그냥 열어보기. JSON 응답이 오면 OK:
```json
{ "ok": true, "message": "POST events.json with ?token=...", "calendar": "primary" }
```

### 4-2. PowerShell에서 단일 이벤트 테스트
```powershell
$url   = $env:GCAL_APPSCRIPT_URL
$token = $env:GCAL_APPSCRIPT_TOKEN
$body  = @{
    events = @(@{
        outlook_entry_id = "test-001"
        subject          = "Apps Script 연결 테스트"
        start            = (Get-Date).AddHours(1).ToString("yyyy-MM-ddTHH:mm:ss")
        end              = (Get-Date).AddHours(2).ToString("yyyy-MM-ddTHH:mm:ss")
        location         = "테스트"
        body             = "테스트 이벤트입니다 — Apps Script로 등록됨"
        is_all_day       = $false
    })
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method Post -Uri "$url`?token=$token" `
    -Body $body -ContentType "application/json; charset=utf-8"
```

응답:
```json
{ "ok": true, "received": 1, "counters": { "new": 1, "upd": 0, "skip": 0, "err": 0 }, "errors": [] }
```

Google Calendar 웹에서 1시간 후 슬롯에 "Apps Script 연결 테스트" 이벤트
보이면 성공.

### 4-3. 실제 추출 + 등록 한 사이클
```powershell
cd <repo-root>\infra\scripts\outlook_to_gcal
.\run.ps1 -DaysAhead 7
```

## 5. 운영 시 주의

- **URL + secret 노출 금지**: 누구든 둘 다 알면 본인 캘린더에 임의로
  쓸 수 있음. URL은 Google이 자동 생성한 추측 불가 hash지만, secret이
  새는 순간 무방비.
- **secret 변경**: `Code.gs`의 `SHARED_SECRET` 바꾸면 새 배포(v2) 발행.
  PowerShell `.env`도 같이 갱신.
- **재배포**: 코드 수정 후 **배포** → **배포 관리** → 기존 배포 옆 ✏️ →
  버전 새로 만들기. URL은 동일하게 유지됨 (배포 ID 같으면).
- **할당량**: Apps Script 무료 quota는 일 6시간 실행. 본 워크플로우
  1회 ≪ 1초.

## 비교: 이 방식 vs OAuth Cloud Console

| 항목 | Apps Script Web App | OAuth Cloud Console |
|---|---|---|
| Cloud Console 가입/결제 화면 | 0회 (안 거침) | 1회 (결제 등록은 안 해도 OK) |
| OAuth 동의 팝업 | 1회 (Apps Script 권한) | 1회 (Calendar 접근) |
| Refresh token 만료 | 없음 (본인이 본인 권한 실행) | 7일 (Test mode) → publish 시 영구 |
| Python 의존성 | 없음 | google-api-python-client |
| 인증 비밀 | shared secret 1개 (.env) | credentials.json + token.json |
| 보안 모델 | URL+secret 보호. 노출 시 캘린더 무방비 | OAuth scope 제어. token 탈취 시 같은 권한 |

이 프로젝트는 Apps Script 패턴을 default로 채택. OAuth 패턴은
[../register_to_gcal.py](../register_to_gcal.py)에 alternative로 보존됨.
