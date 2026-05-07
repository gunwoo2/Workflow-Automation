"""Create a new Project row in Notion.

Run:
  python .notion/create_project.py --name "LG Chem S/4HANA Migration"
  python .notion/create_project.py --name "..." --company-pk CO-0001 \\
      --start 2026-06-01 --end 2026-12-31 --methodology Waterfall \\
      --my-role PMO --sap-modules FI,CO,MM --business-areas BA-FIN-FX,BA-FIN-AR \\
      --scaffold

Behavior:
  - Auto-generates PK as PRJ-YYYY-NNN by scanning existing Project rows for
    the same start-year and incrementing the max sequence.
  - Idempotent on `name`: if a Project with the same `name` already exists,
    prints its PK and exits without creating a duplicate.
  - --scaffold: also creates a Kickoff Meeting (status=scheduled, datetime
    = start_date 09:00 KST) and 5 phase placeholder Deliverables
    (analysis/design/build/test/migration), all linked to the Project.

Stdlib only. Requires .env with NOTION_TOKEN + .notion/db_ids.json populated
by setup.py.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

# Reuse helpers from setup.py
from setup import (  # noqa: E402
    API_BASE, ENV_PATH, DB_IDS_PATH, NotionError,
    load_env, load_db_ids, http,
)

# Force UTF-8 stdout for Windows
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")


# ---------- Notion lookups ----------

def query_db(token, db_id, filter_obj=None, page_size=100):
    out = []
    cursor = None
    while True:
        body = {"page_size": page_size}
        if filter_obj is not None:
            body["filter"] = filter_obj
        if cursor:
            body["start_cursor"] = cursor
        resp = http("POST", f"{API_BASE}/databases/{db_id}/query", token, body)
        out.extend(resp.get("results", []))
        if not resp.get("has_more"):
            return out
        cursor = resp.get("next_cursor")


def page_pk(page):
    title_prop = page["properties"].get("pk", {}).get("title", [])
    return "".join(t.get("plain_text", "") for t in title_prop)


def page_text(page, prop_name):
    p = page["properties"].get(prop_name, {})
    if "rich_text" in p:
        return "".join(t.get("plain_text", "") for t in p["rich_text"])
    if "title" in p:
        return "".join(t.get("plain_text", "") for t in p["title"])
    return ""


def find_company_id(token, company_db_id, company_pk):
    pages = query_db(token, company_db_id, {
        "property": "pk",
        "title": {"equals": company_pk},
    })
    if not pages:
        sys.exit(f"[error] Company {company_pk} not found in Notion. "
                 f"Create it first or omit --company-pk.")
    return pages[0]["id"]


def find_master_relations(token, db_id, pks):
    """Return list of {id} for each master row whose pk matches the input."""
    if not pks:
        return []
    out = []
    for pk in pks:
        pages = query_db(token, db_id, {
            "property": "pk",
            "title": {"equals": pk},
        })
        if not pages:
            print(f"  warn: master pk '{pk}' not found, skipping")
            continue
        out.append({"id": pages[0]["id"]})
    return out


def next_project_seq(token, project_db_id, year):
    """Find the next NNN for PRJ-{year}-NNN by scanning existing rows."""
    prefix = f"PRJ-{year}-"
    pages = query_db(token, project_db_id, {
        "property": "pk",
        "title": {"starts_with": prefix},
    })
    max_seq = 0
    for p in pages:
        pk = page_pk(p)
        try:
            seq = int(pk[len(prefix):])
            max_seq = max(max_seq, seq)
        except ValueError:
            continue
    return max_seq + 1


def find_existing_project_by_name(token, project_db_id, name):
    pages = query_db(token, project_db_id, {
        "property": "name",
        "rich_text": {"equals": name},
    })
    return pages[0] if pages else None


# ---------- Page builders ----------

def title_prop(text):
    return {"title": [{"type": "text", "text": {"content": text}}]}


def rt_prop(text):
    return {"rich_text": [{"type": "text", "text": {"content": str(text)}}]}


def select_prop(name):
    return {"select": {"name": name}}


def date_prop(start, end=None):
    d = {"start": start}
    if end:
        d["end"] = end
    return {"date": d}


def relation_prop(ids):
    return {"relation": [{"id": i} if isinstance(i, str) else i for i in ids]}


def number_prop(n):
    return {"number": n}


# ---------- Main flows ----------

def create_project(token, db_ids, args):
    project_db_id = db_ids["project"]
    year = args.start.year if args.start else datetime.now().year

    existing = find_existing_project_by_name(token, project_db_id, args.name)
    if existing:
        pk = page_pk(existing)
        print(f"[skip] project with name '{args.name}' already exists -> {pk}")
        return existing["id"], pk

    seq = next_project_seq(token, project_db_id, year)
    pk = f"PRJ-{year}-{seq:03d}"
    print(f"[plan] new project PK: {pk}")

    props = {
        "pk": title_prop(pk),
        "name": rt_prop(args.name),
        "status": select_prop("proposed"),
    }
    if args.description:
        props["description"] = rt_prop(args.description)
    if args.start:
        props["start_date"] = date_prop(args.start.isoformat())
    if args.end:
        props["end_planned"] = date_prop(args.end.isoformat())
    if args.methodology:
        props["methodology"] = select_prop(args.methodology)
    if args.my_role:
        props["my_role"] = select_prop(args.my_role)
    if args.phase:
        props["phase"] = select_prop(args.phase)
    if args.progress is not None:
        # Notion percent expects 0-1.0
        props["progress_pct"] = number_prop(args.progress / 100.0)

    if args.company_pk:
        company_id = find_company_id(token, db_ids["company"], args.company_pk)
        props["company"] = relation_prop([company_id])
        print(f"  linked company {args.company_pk}")

    if args.sap_modules:
        rels = find_master_relations(
            token, db_ids["sap_module"],
            [m.strip() for m in args.sap_modules.split(",") if m.strip()],
        )
        if rels:
            props["sap_modules"] = relation_prop(rels)
            print(f"  linked {len(rels)} SAP modules")

    if args.business_areas:
        rels = find_master_relations(
            token, db_ids["business_area"],
            [b.strip() for b in args.business_areas.split(",") if b.strip()],
        )
        if rels:
            props["business_areas"] = relation_prop(rels)
            print(f"  linked {len(rels)} business areas")

    resp = http("POST", f"{API_BASE}/pages", token, {
        "parent": {"type": "database_id", "database_id": project_db_id},
        "properties": props,
    })
    print(f"[ok] created {pk} -> {resp['url']}")
    return resp["id"], pk


def scaffold_project(token, db_ids, project_id, project_pk, start_date):
    """Create kickoff Meeting + 5 phase placeholder Deliverables."""
    print("\n[scaffold] creating kickoff meeting + 5 deliverable placeholders")

    # Kickoff Meeting
    meeting_db_id = db_ids["meeting"]
    kickoff_dt = datetime.combine(start_date, datetime.min.time()).replace(hour=9)
    meeting_pk = f"{project_pk}-M-{start_date.strftime('%Y%m%d')}-01"

    meeting_props = {
        "pk": title_prop(meeting_pk),
        "name": rt_prop(f"{project_pk} Kickoff"),
        "status": select_prop("scheduled"),
        "meeting_datetime": date_prop(kickoff_dt.isoformat()),
        "end_datetime": date_prop((kickoff_dt + timedelta(hours=2)).isoformat()),
        "meeting_type": select_prop("킥오프"),
        "agenda": rt_prop("프로젝트 범위 / 마일스톤 / 핵심 인원 합의"),
        "project": relation_prop([project_id]),
    }
    http("POST", f"{API_BASE}/pages", token, {
        "parent": {"type": "database_id", "database_id": meeting_db_id},
        "properties": meeting_props,
    })
    print(f"  [new ] meeting {meeting_pk}")
    time.sleep(0.3)

    # Phase deliverable placeholders
    deliv_db_id = db_ids["deliverable"]
    phases = [
        ("analysis", "As-Is", "As-Is 프로세스 분석서"),
        ("design", "To-Be", "To-Be 프로세스 설계서"),
        ("build", "화면설계서", "기능별 화면 설계서"),
        ("test", "UAT", "UAT 시나리오 + 결과서"),
        ("migration", "정책", "이행 정책서"),
    ]
    for i, (phase, deliv_type, deliv_name) in enumerate(phases, start=1):
        deliv_pk = f"{project_pk}-D-{i:03d}"
        props = {
            "pk": title_prop(deliv_pk),
            "name": rt_prop(deliv_name),
            "status": select_prop("planned"),
            "phase": select_prop(phase),
            "deliverable_type": select_prop(deliv_type),
            "is_milestone": {"checkbox": True},
            "asset_extracted": {"checkbox": False},
            "project": relation_prop([project_id]),
        }
        http("POST", f"{API_BASE}/pages", token, {
            "parent": {"type": "database_id", "database_id": deliv_db_id},
            "properties": props,
        })
        print(f"  [new ] deliverable {deliv_pk} ({phase})")
        time.sleep(0.3)


def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def main():
    parser = argparse.ArgumentParser(description="Create a new Notion Project row.")
    parser.add_argument("--name", required=True, help="프로젝트 이름")
    parser.add_argument("--description", help="설명")
    parser.add_argument("--company-pk", help="회사 PK (예: CO-0001)")
    parser.add_argument("--start", type=parse_date, help="시작일 YYYY-MM-DD (default: today)")
    parser.add_argument("--end", type=parse_date, help="종료 예정일 YYYY-MM-DD")
    parser.add_argument("--methodology", choices=["Waterfall", "Agile", "Hybrid"])
    parser.add_argument("--my-role", choices=["PM", "PMO", "PL", "Senior", "Consultant", "Junior"])
    parser.add_argument("--phase", default="proposal",
                        choices=["proposal", "analysis", "design", "build", "test",
                                 "migration", "stabilize", "done", "hold"])
    parser.add_argument("--progress", type=int, help="진행률 0-100")
    parser.add_argument("--sap-modules", help="콤마 구분 (예: FI,CO,MM)")
    parser.add_argument("--business-areas", help="콤마 구분 (예: BA-FIN-FX,BA-FIN-AR)")
    parser.add_argument("--scaffold", action="store_true",
                        help="kickoff meeting + 5 phase deliverable 자동 생성")
    args = parser.parse_args()

    if args.start is None:
        args.start = datetime.now().date()

    env = load_env()
    token = env["NOTION_TOKEN"]
    db_ids = load_db_ids()
    if not db_ids:
        sys.exit("[error] .notion/db_ids.json missing. Run setup.py first.")

    project_id, project_pk = create_project(token, db_ids, args)

    if args.scaffold:
        scaffold_project(token, db_ids, project_id, project_pk, args.start)

    print("\n[done]")


if __name__ == "__main__":
    main()
