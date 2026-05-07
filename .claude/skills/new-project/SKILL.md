---
name: new-project
description: Bootstrap a new Project row in Notion. User says "새프로젝트 X" / "프로젝트 만들어줘 ..." / "/new-project ..." — collect required + optional fields, then call .notion/create_project.py to create the Project (and optionally a kickoff Meeting + 5 phase Deliverable placeholders).
---

# new-project SKILL

이 SKILL은 사용자가 새 프로젝트를 시작할 때 노션 Project DB에 1개 row를
정확히, 멱등하게, 표준 PK 패턴(`PRJ-YYYY-NNN`)으로 생성한다.

## When to invoke

사용자가 다음 중 하나를 말할 때:
- "새프로젝트 만들어줘", "새 프로젝트 X", "프로젝트 추가"
- "PRJ-{...} 만들어줘"
- 슬래시: `/new-project ...`
- 직접 회사명 + 시작일을 함께 언급 ("LG화학 S/4HANA 6월부터 시작…")

## Required input

- **`name`** — 프로젝트 이름 (예: "LG화학 S/4HANA 마이그레이션"). 사람이
  읽는 자유 텍스트, PK는 자동 생성된다.

## Optional input (값이 명확할 때만 채움)

| 필드 | 형식 | 비고 |
|---|---|---|
| `description` | 자유 텍스트 | 1-2문장. 길어지면 노션에서 직접 추가 권유 |
| `company_pk` | `CO-NNNN` | 회사가 Company DB에 이미 있어야 함 |
| `start` | `YYYY-MM-DD` | default: 오늘. PK 연도가 이 날짜 기준 |
| `end` | `YYYY-MM-DD` | 종료 예정일 |
| `methodology` | `Waterfall` / `Agile` / `Hybrid` | SAP 프로젝트는 보통 Waterfall |
| `my_role` | `PM` / `PMO` / `PL` / `Senior` / `Consultant` / `Junior` | |
| `phase` | `proposal` / `analysis` / `design` / `build` / `test` / `migration` / `stabilize` / `done` / `hold` | default: `proposal` |
| `progress` | 0-100 | 노션은 percent (0.0-1.0)로 저장. 스크립트가 변환 |
| `sap_modules` | `FI,CO,MM` 콤마 구분 | SAP Module 마스터의 PK |
| `business_areas` | `BA-FIN-FX,BA-FIN-AR` 콤마 구분 | Business Area 마스터의 PK |
| `scaffold` | true/false | true 시 kickoff Meeting + 5 phase Deliverable 자동 생성 |

## Procedure

1. **사용자 발화에서 입력 추출** — 위 표 기준으로 자연어에서 직접 매핑.
   불명확한 필수값(`name`)만 한 번 묻고, 나머지는 비워둔 채 진행한다.
   (KP1 Think Before Coding: 가정을 명시하되, 알 수 있는 건 그냥 채움.)

2. **검증** — `company_pk` / `sap_modules` / `business_areas`는 Company /
   SAP Module / Business Area DB에 실제 존재하는 PK여야 함. 스크립트가
   조회 후 없으면 경고하고 해당 relation만 skip한다.

3. **실행** — 다음 명령을 Bash로 실행:

   ```bash
   python .notion/create_project.py \
     --name "<name>" \
     [--company-pk CO-NNNN] \
     [--start YYYY-MM-DD] \
     [--end YYYY-MM-DD] \
     [--methodology Waterfall] \
     [--my-role PMO] \
     [--phase proposal] \
     [--sap-modules FI,CO,MM] \
     [--business-areas BA-FIN-FX] \
     [--scaffold]
   ```

   (Windows PowerShell에서는 `\` 대신 백틱 `` ` ``으로 줄바꿈 또는 한
   줄로 작성.)

4. **결과 보고** — 스크립트 출력을 사용자에게 그대로 보여주고, 마지막에
   생성된 Project URL을 한 줄로 강조한다.

## Idempotency

같은 `name`으로 다시 호출하면 스크립트가 기존 PK를 출력하고 종료한다.
새 PK를 강제하려면 `name`을 바꾸거나, 기존 row를 노션에서 archive 후
재실행한다.

## Examples

### 최소 호출 (KP2 Simplicity First)
```
사용자: 새프로젝트 만들어줘 — "LG화학 S/4HANA"
스킬: python .notion/create_project.py --name "LG화학 S/4HANA"
결과: PRJ-2026-001 생성, status=proposed
```

### 표준 호출 (회사 + SAP 모듈 명시)
```
사용자: LG화학에서 6월부터 12월까지 FI/CO 마이그레이션 PMO 역할로
스킬: python .notion/create_project.py \
       --name "LG화학 FI/CO 마이그레이션" \
       --company-pk CO-0001 \
       --start 2026-06-01 --end 2026-12-31 \
       --methodology Waterfall --my-role PMO \
       --sap-modules FI,CO
```

### 스캐폴드 포함
```
사용자: SK에너지 S/4HANA 프로젝트 만들고 킥오프 미팅이랑 산출물 placeholder까지
스킬: python .notion/create_project.py \
       --name "SK에너지 S/4HANA" \
       --company-pk CO-0002 \
       --scaffold
결과: Project + Kickoff Meeting + 5 Deliverable placeholders 일괄 생성
```

## Out of scope (이 SKILL은 하지 않는다)

- **Company / Person 신규 생성** — 별도 SKILL 또는 노션에서 직접
- **상세 Task 분해** — Phase 2/Hermes 분류 SKILL이 인박스 입력에서
  도출하는 영역
- **OneDrive 폴더 생성, GitHub 레포 fork** — Phase 2 이후 외부 시스템
  연동에서 처리

## References

- [.notion/create_project.py](../../../.notion/create_project.py) — 실제 mutation 로직
- [.notion/schema.py](../../../.notion/schema.py) — Project 필드 정의
- [notion-db-spec.md](../../../notion-db-spec.md) §P0 Project — 스펙 SSoT
- [SOUL.md](../../../SOUL.md) §3 KP1~KP4 — 의사결정 원칙
