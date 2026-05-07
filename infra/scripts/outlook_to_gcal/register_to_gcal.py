"""Push events from extract_events.ps1 output JSON into Google Calendar.

Idempotent: each event is matched by `outlook_entry_id` stored in
`extendedProperties.private` so re-running the same JSON updates existing
events instead of duplicating.

First-time setup:
  1. Google Cloud Console → create project → enable "Google Calendar API"
  2. APIs & Services → Credentials → Create OAuth client ID
       application type: Desktop app
  3. Download JSON → save as `credentials.json` next to this script
  4. pip install google-auth google-auth-oauthlib google-api-python-client
  5. First run opens a browser for one-time consent. token.json is then
     cached locally (refresh-token-based, no further interaction).

Usage:
  python register_to_gcal.py events.json
  python register_to_gcal.py events.json --calendar-id primary
  python register_to_gcal.py events.json --dry-run
"""

import argparse
import json
import sys
from pathlib import Path

# Force UTF-8 stdout on Windows
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    sys.exit(
        "[error] Google API libs not installed.\n"
        "  Run: pip install google-auth google-auth-oauthlib google-api-python-client"
    )

SCRIPT_DIR = Path(__file__).resolve().parent
CREDS_PATH = SCRIPT_DIR / "credentials.json"
TOKEN_PATH = SCRIPT_DIR / "token.json"
SCOPES = ["https://www.googleapis.com/auth/calendar"]


# ---------- OAuth ----------

def get_service():
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_PATH.exists():
                sys.exit(
                    f"[error] {CREDS_PATH} missing.\n"
                    "  See README §1 for Google Cloud OAuth client setup."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


# ---------- Event mapping ----------

def event_to_gcal_body(ev):
    body = {
        "summary": ev.get("subject") or "(no title)",
        "description": ev.get("body", "") or "",
        "location": ev.get("location", "") or "",
        "extendedProperties": {
            "private": {
                "outlook_entry_id": ev["outlook_entry_id"],
                "outlook_organizer": ev.get("organizer", "") or "",
            }
        },
    }
    tz = ev.get("timezone") or "Asia/Seoul"
    if ev.get("is_all_day"):
        body["start"] = {"date": ev["start"][:10]}
        body["end"] = {"date": ev["end"][:10]}
    else:
        body["start"] = {"dateTime": ev["start"], "timeZone": tz}
        body["end"] = {"dateTime": ev["end"], "timeZone": tz}
    return body


def find_event(service, calendar_id, entry_id):
    resp = service.events().list(
        calendarId=calendar_id,
        privateExtendedProperty=f"outlook_entry_id={entry_id}",
        showDeleted=False,
        singleEvents=False,
        maxResults=1,
    ).execute()
    items = resp.get("items", [])
    return items[0] if items else None


def needs_update(existing, body):
    """Cheap diff: title, start, end, location, description."""
    if existing.get("summary") != body["summary"]:
        return True
    if existing.get("location", "") != body.get("location", ""):
        return True
    if existing.get("description", "") != body.get("description", ""):
        return True
    for key in ("start", "end"):
        a, b = existing.get(key, {}), body.get(key, {})
        if a.get("dateTime") != b.get("dateTime") or a.get("date") != b.get("date"):
            return True
    return False


# ---------- Sync ----------

def sync_events(payload, calendar_id, dry_run=False):
    service = get_service() if not dry_run else None
    counters = {"new": 0, "upd": 0, "skip": 0, "err": 0}

    for ev in payload.get("events", []):
        subject = (ev.get("subject") or "(no title)").strip()
        body = event_to_gcal_body(ev)
        entry_id = ev["outlook_entry_id"]

        if dry_run:
            print(f"  [dry ] {subject[:50]}  ({ev['start']} → {ev['end']})")
            counters["new"] += 1
            continue

        try:
            existing = find_event(service, calendar_id, entry_id)
            if existing:
                if not needs_update(existing, body):
                    print(f"  [skip] {subject[:50]}")
                    counters["skip"] += 1
                    continue
                service.events().update(
                    calendarId=calendar_id, eventId=existing["id"], body=body,
                ).execute()
                print(f"  [upd ] {subject[:50]}")
                counters["upd"] += 1
            else:
                service.events().insert(calendarId=calendar_id, body=body).execute()
                print(f"  [new ] {subject[:50]}")
                counters["new"] += 1
        except HttpError as e:
            print(f"  [err ] {subject[:50]}  -> {e}")
            counters["err"] += 1

    print(f"\nDone: new={counters['new']} updated={counters['upd']} "
          f"skipped={counters['skip']} errors={counters['err']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="events.json from extract_events.ps1")
    parser.add_argument("--calendar-id", default="primary",
                        help="Google Calendar ID (default: primary)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print intended actions without calling Google API")
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        sys.exit(f"[error] {in_path} not found")
    payload = json.loads(in_path.read_text(encoding="utf-8"))

    print(f"Source: {in_path}")
    print(f"  extracted_at: {payload.get('extracted_at')}")
    print(f"  events: {payload.get('events_count')}, tasks: {payload.get('tasks_count')}")
    print(f"  target calendar: {args.calendar_id}\n")

    sync_events(payload, args.calendar_id, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
