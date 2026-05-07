# `.notion/` — Phase 1 Notion DB bootstrapper

Creates the 10 Phase 1 databases (Tier 0 / Tier 1 / Tier 2 / Inbox) under a
parent Notion page in one idempotent run. Stdlib only — no `pip install`
required.

## Files

| File | Purpose |
|---|---|
| `setup.py` | Entry point. 3-pass create + seed. |
| `schema.py` | All 10 DB schemas (single source, codified from `notion-db-spec.md`). |
| `seed_data.py` | SAP Module (19) + Business Area (parents 6 + children 20) seed rows. |
| `db_ids.json` | Created at runtime. Maps `db_key -> notion_database_id`. **Gitignored.** |
| `README.md` | This file. |

## Prerequisites

1. **Notion integration** at https://www.notion.so/profile/integrations — create
   one and grab its Internal Integration Token (`ntn_...`).
2. **Share parent page with the integration**. Open the parent page in Notion
   → click `...` (top right) → `Connections` → add your integration. *Without
   this, the API returns 404.*
3. **Python 3.10+** (`python --version` or `py --version`).

## Configure

Copy `.env.example` to `.env` at the repo root and fill in:

```ini
NOTION_TOKEN=ntn_your_token_here
PARENT_PAGE_ID=your_parent_page_id
```

`.env` is gitignored.

## Run

```powershell
# Windows PowerShell
cd C:\path\to\Workflow-Automation
python .notion\setup.py
```

```bash
# macOS / Linux
cd /path/to/Workflow-Automation
python .notion/setup.py
```

Expected output (first run):

```
[ok] auth as bot 'Life OS Bot' (id 12345678...)

--- pass 1: create databases ---
  [new  ] Company        create -> 1f5...
  [new  ] Person         create -> 1f6...
  ...

--- pass 2: add relation properties ---
  [add  ] Company        += source_inbox
  [add  ] Person         += current_company, source_inbox
  ...

--- pass 3: seed master data ---
  SAP Module:
    [new ] FI
    [new ] CO
    ...
  Business Area parents:
    [new ] BA-FIN
    ...
  Business Area children:
    [new ] BA-FIN-FX  (parent=BA-FIN)
    ...

--- summary ---
  parent page: https://www.notion.so/your_parent_page_id
  🏢 Company        https://www.notion.so/...
  ...
```

## Re-running

Safe. Each pass detects existing state:

- Pass 1 — looks up DB ID in `db_ids.json` (verified live), then falls back
  to scanning child blocks of the parent page by title.
- Pass 2 — fetches each DB's current properties; only adds missing relations.
- Pass 3 — queries each DB by `pk` (Title) and skips matches.

## What gets created (Phase 1, 10 DBs)

| Tier | DB | PK pattern |
|---|---|---|
| 0 | Company | `CO-NNNN` |
| 0 | Person | `PE-NNNN` |
| 0 | SAP Module | `FI`, `CO`, `MM`, … (standard codes) |
| 0 | Business Area | `BA-XXX` / `BA-XXX-YYY` |
| 1 | Project | `PRJ-YYYY-NNN` |
| 2 | Task | `[Proj]-T-NNNN` |
| 2 | Deliverable | `[Proj]-D-NNN` |
| 2 | Meeting | `[Proj]-M-YYYYMMDD-NN` |
| 2 | Risk | `[Proj]-R-NNN` |
| ALL | Inbox | `IBX-YYYYMMDD-NNNN` |

## Phase 2 (deferred)

Adds 5 more DBs (PCH, Case, Error, Resource, Template) and 4 more
`routed_to_*` relations on Inbox. Not in this script — see
`notion-db-spec.md` §Phase 2.

## Verification checklist

After running, open the parent page in Notion and confirm:

- [ ] 10 child databases visible
- [ ] SAP Module has 19 rows
- [ ] Business Area has 26 rows (6 parents + 20 children)
- [ ] Business Area children show their `parent_area` populated
- [ ] Project has 5 relation columns (company, key_persons, sap_modules,
  business_areas, source_inbox)
- [ ] Inbox has 7 `routed_to_*` columns + `mentioned_people` /
  `mentioned_companies` / `inferred_project`
- [ ] Risk's `priority` column exists (created as Select; convert to Formula
  manually — see "Risk priority formula" below)

## Risk priority formula (manual step)

`priority` is created as a `Select` because Notion's create-DB endpoint
rejects formulas referencing other Select properties in the same request
(`Type error with formula`). Convert it to a Formula in the UI:

1. Open the **Risk** DB → click `priority` column header → **Edit property**
   → change type to **Formula**.
2. Paste this expression:

   ```
   if(and(format(prop("impact")) == "High", format(prop("probability")) == "High"), "High",
   if(or(
     and(format(prop("impact")) == "High", format(prop("probability")) == "Medium"),
     and(format(prop("impact")) == "Medium", format(prop("probability")) == "High"),
     and(format(prop("impact")) == "Medium", format(prop("probability")) == "Medium")
   ), "Medium", "Low"))
   ```

   Maps the 3×3 impact×probability matrix to High / Medium / Low.

## Troubleshooting

**`HTTP 404` on `/blocks/{parent}/children`** — the integration isn't shared
with the parent page. Re-do step 2 of Prerequisites.

**`HTTP 401`** — bad/expired token. Rotate at the integrations page and
update `.env`.

**`HTTP 400 ... validation_error` on formula** — Notion's create-DB endpoint
rejects formulas that reference other props in the same request. The script
sidesteps this by creating `Risk.priority` as a Select; convert it to a
Formula manually (see "Risk priority formula" above).

**Duplicate DBs created** — happens if the previous run partially failed
*and* the parent page already had a DB with the same title from a manual
attempt. Delete extras manually; `db_ids.json` will pin the correct one.
