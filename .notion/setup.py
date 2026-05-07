"""Phase 1 Notion DB bootstrapper.

Run:  python .notion/setup.py

Behavior:
  1. Load .env (NOTION_TOKEN, PARENT_PAGE_ID).
  2. Verify token via /users/me.
  3. Pass 1 — create 10 DBs under PARENT_PAGE_ID (no relation properties).
  4. Pass 2 — patch each DB to add relation properties (cross-DB + self).
  5. Pass 3 — seed SAP Module (19 rows) + Business Area (parents + children).
  6. Save .notion/db_ids.json (gitignored).

Idempotent: re-running skips already-created DBs (matched by title under the
parent page) and existing rows (matched by pk). Stdlib only.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Windows console defaults to CP949/CP1252; force UTF-8 so emoji + Korean
# render in stdout without UnicodeEncodeError.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import schema  # noqa: E402
import seed_data  # noqa: E402

NOTION_VERSION = "2022-06-28"
API_BASE = "https://api.notion.com/v1"
DB_IDS_PATH = SCRIPT_DIR / "db_ids.json"
ENV_PATH = SCRIPT_DIR.parent / ".env"


# ---------- env / state ----------

def load_env():
    if not ENV_PATH.exists():
        sys.exit(f"[error] .env not found at {ENV_PATH}")
    env = {}
    for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    for required in ("NOTION_TOKEN", "PARENT_PAGE_ID"):
        if not env.get(required):
            sys.exit(f"[error] {required} missing in .env")
    return env


def load_db_ids():
    if DB_IDS_PATH.exists():
        return json.loads(DB_IDS_PATH.read_text(encoding="utf-8"))
    return {}


def save_db_ids(db_ids):
    DB_IDS_PATH.write_text(
        json.dumps(db_ids, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def normalize_uuid(s):
    s = s.replace("-", "").strip()
    if len(s) != 32:
        return s
    return f"{s[0:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:32]}"


# ---------- HTTP ----------

class NotionError(RuntimeError):
    def __init__(self, status, body, url):
        self.status = status
        self.body = body
        self.url = url
        super().__init__(f"HTTP {status} {url}: {body}")


def http(method, url, token, body=None, retries=4):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
            "User-Agent": "life-os-setup/0.1",
        },
    )
    last_err = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = resp.read().decode("utf-8")
                return json.loads(payload) if payload else {}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            if e.code == 429:
                wait = float(e.headers.get("Retry-After", "1"))
                print(f"    rate limited; sleeping {wait}s")
                time.sleep(wait)
                continue
            if e.code in (502, 503, 504):
                time.sleep(2 ** attempt)
                last_err = NotionError(e.code, err_body, url)
                continue
            raise NotionError(e.code, err_body, url) from e
        except urllib.error.URLError as e:
            last_err = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"failed after {retries} attempts to {url}: {last_err}")


# ---------- pass 1: create DBs ----------

def verify_token(token):
    me = http("GET", f"{API_BASE}/users/me", token)
    print(f"[ok] auth as bot '{me.get('name', '?')}' (id {me.get('id', '?')[:8]}...)")


def find_existing_db_in_page(token, parent_page_id, title_to_find):
    cursor = None
    while True:
        url = f"{API_BASE}/blocks/{parent_page_id}/children?page_size=100"
        if cursor:
            url += f"&start_cursor={cursor}"
        try:
            resp = http("GET", url, token)
        except NotionError as e:
            if e.status == 404:
                sys.exit(
                    "[error] parent page not accessible. share it with your "
                    "integration: open the page in Notion, click '...', "
                    "Connections -> add your integration."
                )
            raise
        for block in resp.get("results", []):
            if block.get("type") == "child_database":
                if block["child_database"].get("title") == title_to_find:
                    return block["id"]
        if not resp.get("has_more"):
            return None
        cursor = resp.get("next_cursor")


def create_database(token, parent_page_id, db_def):
    body = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "icon": {"type": "emoji", "emoji": db_def["icon"]},
        "title": [{"type": "text", "text": {"content": db_def["title"]}}],
        "description": [{"type": "text", "text": {"content": db_def.get("description", "")}}],
        "properties": db_def["pass1_props"],
    }
    return http("POST", f"{API_BASE}/databases", token, body)["id"]


def pass1_create_dbs(token, parent_page_id, db_ids):
    print("\n--- pass 1: create databases ---")
    for key, db_def in schema.DATABASES.items():
        # cached id?
        if key in db_ids:
            try:
                http("GET", f"{API_BASE}/databases/{db_ids[key]}", token)
                print(f"  [skip ] {db_def['title']:<14} cached -> {db_ids[key]}")
                continue
            except NotionError:
                print(f"  cached id stale for {key}; rediscovering")
        # search parent
        existing = find_existing_db_in_page(token, parent_page_id, db_def["title"])
        if existing:
            db_ids[key] = existing
            print(f"  [reuse] {db_def['title']:<14} found  -> {existing}")
        else:
            new_id = create_database(token, parent_page_id, db_def)
            db_ids[key] = new_id
            print(f"  [new  ] {db_def['title']:<14} create -> {new_id}")
        save_db_ids(db_ids)
        time.sleep(0.35)


# ---------- pass 2: add relations ----------

def pass2_add_relations(token, db_ids):
    print("\n--- pass 2: add relation properties ---")
    for key, db_def in schema.DATABASES.items():
        relations = db_def.get("relations", [])
        if not relations:
            continue
        db_id = db_ids[key]
        current = http("GET", f"{API_BASE}/databases/{db_id}", token)
        existing_props = set(current.get("properties", {}).keys())
        to_add = {}
        for rel in relations:
            if rel["prop"] in existing_props:
                continue
            target_id = db_ids.get(rel["target"])
            if not target_id:
                print(f"    skip {key}.{rel['prop']} -> target {rel['target']} not in db_ids")
                continue
            to_add[rel["prop"]] = schema.relation_property(target_id, rel["kind"])
        if not to_add:
            print(f"  [skip] {db_def['title']:<14} (all relations exist)")
            continue
        http("PATCH", f"{API_BASE}/databases/{db_id}", token, {"properties": to_add})
        print(f"  [add ] {db_def['title']:<14} += {', '.join(to_add)}")
        time.sleep(0.35)


# ---------- pass 3: seed data ----------

def query_pks(token, db_id):
    out = {}
    cursor = None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        resp = http("POST", f"{API_BASE}/databases/{db_id}/query", token, body)
        for page in resp.get("results", []):
            title_prop = page["properties"].get("pk", {}).get("title", [])
            if title_prop:
                pk = "".join(t.get("plain_text", "") for t in title_prop)
                out[pk] = page["id"]
        if not resp.get("has_more"):
            return out
        cursor = resp.get("next_cursor")


def build_page_props(record, schema_props):
    """Convert a flat record dict into Notion property-value JSON, driven by
    the schema's property type for each field."""
    out = {}
    for field, value in record.items():
        if field == "parent_pk" or value in (None, ""):
            continue
        if field == "pk":
            out["pk"] = {"title": [{"type": "text", "text": {"content": str(value)}}]}
            continue
        prop_def = schema_props.get(field)
        if prop_def is None:
            continue
        if "rich_text" in prop_def:
            out[field] = {"rich_text": [{"type": "text", "text": {"content": str(value)}}]}
        elif "select" in prop_def:
            out[field] = {"select": {"name": str(value)}}
        elif "multi_select" in prop_def:
            vals = value if isinstance(value, list) else [value]
            out[field] = {"multi_select": [{"name": str(v)} for v in vals]}
        elif "number" in prop_def:
            out[field] = {"number": float(value)}
        elif "url" in prop_def:
            out[field] = {"url": str(value)}
        elif "email" in prop_def:
            out[field] = {"email": str(value)}
        elif "phone_number" in prop_def:
            out[field] = {"phone_number": str(value)}
        elif "date" in prop_def:
            out[field] = {"date": {"start": str(value)}}
        elif "checkbox" in prop_def:
            out[field] = {"checkbox": bool(value)}
    return out


def create_page(token, db_id, props):
    return http("POST", f"{API_BASE}/pages", token, {
        "parent": {"type": "database_id", "database_id": db_id},
        "properties": props,
    })


def pass3_seed(token, db_ids):
    print("\n--- pass 3: seed master data ---")

    # SAP Module
    print("  SAP Module:")
    db_id = db_ids["sap_module"]
    schema_props = schema.DATABASES["sap_module"]["pass1_props"]
    existing = query_pks(token, db_id)
    for record in seed_data.SAP_MODULES:
        pk = record["pk"]
        if pk in existing:
            print(f"    [skip] {pk}")
            continue
        create_page(token, db_id, build_page_props(record, schema_props))
        print(f"    [new ] {pk}")
        time.sleep(0.3)

    # Business Area parents
    print("  Business Area parents:")
    db_id = db_ids["business_area"]
    schema_props = schema.DATABASES["business_area"]["pass1_props"]
    existing = query_pks(token, db_id)
    parent_id_by_pk = dict(existing)
    for record in seed_data.BUSINESS_AREA_PARENTS:
        pk = record["pk"]
        if pk in existing:
            print(f"    [skip] {pk}")
            continue
        resp = create_page(token, db_id, build_page_props(record, schema_props))
        parent_id_by_pk[pk] = resp["id"]
        print(f"    [new ] {pk}")
        time.sleep(0.3)

    # Business Area children + parent_area link
    print("  Business Area children:")
    existing = query_pks(token, db_id)
    for record in seed_data.BUSINESS_AREA_CHILDREN:
        pk = record["pk"]
        if pk in existing:
            print(f"    [skip] {pk}")
            continue
        props = build_page_props(record, schema_props)
        parent_id = parent_id_by_pk.get(record.get("parent_pk")) or existing.get(record.get("parent_pk"))
        if parent_id:
            props["parent_area"] = {"relation": [{"id": parent_id}]}
        create_page(token, db_id, props)
        print(f"    [new ] {pk}  (parent={record.get('parent_pk')})")
        time.sleep(0.3)


# ---------- summary ----------

def print_summary(db_ids, parent_page_id):
    print("\n--- summary ---")
    print(f"  parent page: https://www.notion.so/{parent_page_id.replace('-', '')}")
    for key, db_def in schema.DATABASES.items():
        db_id = db_ids.get(key, "?")
        link = f"https://www.notion.so/{db_id.replace('-', '')}" if db_id != "?" else "(missing)"
        print(f"  {db_def['icon']} {db_def['title']:<14} {link}")
    print(f"\n  db_ids saved -> {DB_IDS_PATH}")


def main():
    env = load_env()
    token = env["NOTION_TOKEN"]
    parent_page_id = normalize_uuid(env["PARENT_PAGE_ID"])

    verify_token(token)

    db_ids = load_db_ids()
    pass1_create_dbs(token, parent_page_id, db_ids)
    pass2_add_relations(token, db_ids)
    pass3_seed(token, db_ids)
    print_summary(db_ids, parent_page_id)


if __name__ == "__main__":
    main()
