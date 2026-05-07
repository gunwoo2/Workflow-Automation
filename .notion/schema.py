"""Phase 1 Notion DB schema definitions (10 DBs).

Single source: notion-db-spec.md. setup.py consumes this in 3 passes:
  pass 1 -> create DBs with non-relation properties only
  pass 2 -> patch each DB to add relation properties
  pass 3 -> seed master data (SAP Module, Business Area)

Property spec follows Notion API 2022-06-28 schema. Keep field names in
snake_case to match the spec exactly. Korean display labels are kept on
Select/Multi-select option `name` fields per the spec's "codeval (display)"
convention.
"""

from collections import OrderedDict


# ---------- Notion API property factories ----------

def title():
    return {"title": {}}

def rt():
    return {"rich_text": {}}

def num(fmt="number"):
    return {"number": {"format": fmt}}

def date():
    return {"date": {}}

def url():
    return {"url": {}}

def email():
    return {"email": {}}

def phone():
    return {"phone_number": {}}

def files():
    return {"files": {}}

def checkbox():
    return {"checkbox": {}}

def created_time():
    return {"created_time": {}}

def last_edited_time():
    return {"last_edited_time": {}}

def select(options):
    return {"select": {"options": [{"name": n} for n in options]}}

def multi_select(options):
    return {"multi_select": {"options": [{"name": n} for n in options]}}

def formula(expression):
    return {"formula": {"expression": expression}}


# ---------- Common select option vocabularies ----------

# Status enums (codeval form per spec)
STATUS_COMPANY = ["active", "inactive"]
STATUS_PERSON = ["active", "inactive"]
STATUS_PROJECT = ["proposed", "active", "hold", "done", "archived"]
STATUS_TASK = ["backlog", "todo", "doing", "review", "done", "cancelled"]
STATUS_DELIVERABLE = ["planned", "drafting", "review", "approved", "submitted", "obsolete"]
STATUS_MEETING = ["scheduled", "held", "documented", "cancelled", "noshow"]
STATUS_RISK = ["identified", "mitigating", "resolved", "realized", "closed"]
STATUS_INBOX = ["raw", "classifying", "pending_confirm", "routed", "failed", "trash"]

# Risk priority formula: 3x3 matrix collapsed to High/Medium/Low.
# `prop("...")` on a Select returns an option object — `format(...)` coerces
# to its display name so string comparison works.
RISK_PRIORITY_FORMULA = (
    'if(and(format(prop("impact")) == "High", format(prop("probability")) == "High"), "High", '
    'if(or('
    'and(format(prop("impact")) == "High", format(prop("probability")) == "Medium"), '
    'and(format(prop("impact")) == "Medium", format(prop("probability")) == "High"), '
    'and(format(prop("impact")) == "Medium", format(prop("probability")) == "Medium")'
    '), "Medium", "Low"))'
)


# ---------- Database definitions ----------
#
# Each entry:
#   key:           internal stable key (matches db_ids.json)
#   title:         Notion DB title
#   icon:          emoji
#   description:   Notion DB description
#   pass1_props:   properties created at DB creation time (no relations)
#   relations:     list of dicts added in pass 2:
#                    {prop, target, kind: "single"/"multi", self: bool}

DATABASES = OrderedDict()


# M1. Company
DATABASES["company"] = {
    "title": "Company",
    "icon": "🏢",
    "description": "회사 마스터. 한 페이지 = 한 회사. 동명 회사 중복 방지는 name_hash로 처리.",
    "pass1_props": {
        "pk": title(),
        "name": rt(),
        "description": rt(),
        "status": select(STATUS_COMPANY),
        "name_hash": rt(),
        "aliases": rt(),
        "industry": select(["제조", "유통", "금융", "에너지", "IT", "헬스케어", "물류", "공공", "건설"]),
        "size": select(["대기업", "중견", "중소", "스타트업", "글로벌"]),
        "relationship": select(["고객사", "파트너", "내부", "기타"]),
        "first_contact_date": date(),
        "website": url(),
        "industry_code": rt(),
        "external_refs": rt(),
        "created_time": created_time(),
        "updated_time": last_edited_time(),
    },
    "relations": [
        {"prop": "source_inbox", "target": "inbox", "kind": "single"},
    ],
}


# M2. Person
DATABASES["person"] = {
    "title": "Person",
    "icon": "👤",
    "description": "인물 마스터. 명함 OCR 진입점. 동명이인은 (회사+이름) 해시로 분리.",
    "pass1_props": {
        "pk": title(),
        "name": rt(),
        "description": rt(),
        "status": select(STATUS_PERSON),
        "name_hash": rt(),
        "current_position": rt(),
        "roles": multi_select(["PM", "PO", "개발자", "관리", "임원", "기능", "기획", "QA"]),
        "email": email(),
        "phone": phone(),
        "linkedin_url": url(),
        "business_card_image": files(),
        "first_met_date": date(),
        "first_met_place": rt(),
        "notes": rt(),
        "external_refs": rt(),
        "created_time": created_time(),
        "updated_time": last_edited_time(),
    },
    "relations": [
        {"prop": "current_company", "target": "company", "kind": "single"},
        {"prop": "source_inbox", "target": "inbox", "kind": "single"},
    ],
}


# M3. SAP Module
DATABASES["sap_module"] = {
    "title": "SAP Module",
    "icon": "🧩",
    "description": "SAP 모듈 표준 분류. PK = 표준 코드 그대로 (FI, CO, MM …).",
    "pass1_props": {
        "pk": title(),
        "name": rt(),
        "description": rt(),
        "english_name": rt(),
        "category": select(["Logistics", "Finance", "HR", "Technology", "Cross"]),
        "skill_level": select(["Expert", "Advanced", "Intermediate", "Novice", "NoExperience"]),
        "aliases": rt(),
        "external_refs": rt(),
        "created_time": created_time(),
        "updated_time": last_edited_time(),
    },
    "relations": [],
}


# M4. Business Area
DATABASES["business_area"] = {
    "title": "Business Area",
    "icon": "🗂️",
    "description": "비즈니스 영역 횡단 분류. 부모-자식 자기참조.",
    "pass1_props": {
        "pk": title(),
        "name": rt(),
        "description": rt(),
        "aliases": rt(),
        "external_refs": rt(),
        "created_time": created_time(),
        "updated_time": last_edited_time(),
    },
    "relations": [
        {"prop": "parent_area", "target": "business_area", "kind": "single", "self": True},
    ],
}


# P0. Project
DATABASES["project"] = {
    "title": "Project",
    "icon": "📁",
    "description": "프로젝트 컨테이너. 모든 운영 데이터의 컨테이너.",
    "pass1_props": {
        "pk": title(),
        "name": rt(),
        "description": rt(),
        "status": select(STATUS_PROJECT),
        "phase": select(["proposal", "analysis", "design", "build", "test", "migration", "stabilize", "done", "hold"]),
        "methodology": select(["Waterfall", "Agile", "Hybrid"]),
        "start_date": date(),
        "end_planned": date(),
        "end_actual": date(),
        "progress_pct": num("percent"),
        "my_role": select(["PM", "PMO", "PL", "Senior", "Consultant", "Junior"]),
        "tone_manner": rt(),
        "onedrive_root_path": rt(),
        "github_repo_url": url(),
        "google_calendar_id": rt(),
        "outlook_calendar_id": rt(),
        "outlook_account": rt(),
        "teams_workspace_id": rt(),
        "slack_workspace": rt(),
        "sharepoint_url": url(),
        "external_refs": rt(),
        "created_time": created_time(),
        "updated_time": last_edited_time(),
    },
    "relations": [
        {"prop": "company", "target": "company", "kind": "single"},
        {"prop": "key_persons", "target": "person", "kind": "multi"},
        {"prop": "sap_modules", "target": "sap_module", "kind": "multi"},
        {"prop": "business_areas", "target": "business_area", "kind": "multi"},
        {"prop": "source_inbox", "target": "inbox", "kind": "single"},
    ],
}


# P1. Task
DATABASES["task"] = {
    "title": "Task",
    "icon": "✅",
    "description": "작업/이슈/액션 통합. 회의에서 도출된 액션도 포함.",
    "pass1_props": {
        "pk": title(),
        "name": rt(),
        "description": rt(),
        "status": select(STATUS_TASK),
        "task_type": select(["Task", "Bug", "Story", "Epic", "Action"]),
        "priority": select(["P0", "P1", "P2", "P3"]),
        "due_date": date(),
        "completed_date": date(),
        "estimated_hours": num(),
        "actual_hours": num(),
        "sprint": select(["Sprint 1", "Sprint 2", "Sprint 3", "Sprint 4"]),
        "github_issue_url": url(),
        "github_pr_url": url(),
        "external_refs": rt(),
        "created_time": created_time(),
        "updated_time": last_edited_time(),
    },
    "relations": [
        {"prop": "project", "target": "project", "kind": "single"},
        {"prop": "assignee", "target": "person", "kind": "single"},
        {"prop": "reporter", "target": "person", "kind": "single"},
        {"prop": "parent_task", "target": "task", "kind": "single", "self": True},
        {"prop": "blocks", "target": "task", "kind": "multi", "self": True},
        {"prop": "meetings", "target": "meeting", "kind": "multi"},
        {"prop": "sap_modules", "target": "sap_module", "kind": "multi"},
        {"prop": "source_inbox", "target": "inbox", "kind": "single"},
    ],
}


# P2. Deliverable
DATABASES["deliverable"] = {
    "title": "Deliverable",
    "icon": "📄",
    "description": "단계별 산출물 메타. 실제 파일은 OneDrive.",
    "pass1_props": {
        "pk": title(),
        "name": rt(),
        "description": rt(),
        "status": select(STATUS_DELIVERABLE),
        "phase": select(["analysis", "design", "build", "test", "migration"]),
        "deliverable_type": select(["As-Is", "To-Be", "IF정의서", "화면설계서", "보고", "정책", "UAT", "교육계획", "매뉴얼", "참고자료"]),
        "due_date": date(),
        "submitted_date": date(),
        "version": rt(),
        "is_milestone": checkbox(),
        "asset_extracted": checkbox(),
        "onedrive_item_id": rt(),
        "onedrive_path": rt(),
        "sharepoint_url": url(),
        "file_hash": rt(),
        "external_refs": rt(),
        "created_time": created_time(),
        "updated_time": last_edited_time(),
    },
    "relations": [
        {"prop": "project", "target": "project", "kind": "single"},
        {"prop": "previous_version", "target": "deliverable", "kind": "single", "self": True},
        {"prop": "sap_modules", "target": "sap_module", "kind": "multi"},
        {"prop": "business_areas", "target": "business_area", "kind": "multi"},
        {"prop": "source_inbox", "target": "inbox", "kind": "single"},
        # Phase 2 relations (added later): template_used -> Template
    ],
}


# P3. Meeting
DATABASES["meeting"] = {
    "title": "Meeting",
    "icon": "📅",
    "description": "회의록. scheduled 상태가 곧 캘린더 이벤트.",
    "pass1_props": {
        "pk": title(),
        "name": rt(),
        "description": rt(),
        "status": select(STATUS_MEETING),
        "meeting_datetime": date(),
        "end_datetime": date(),
        "meeting_type": select(["내부", "킥오프", "정기", "워크샵", "고객IF", "세미나", "1on1"]),
        "agenda": rt(),
        "decisions": rt(),
        "raw_memo": rt(),
        "structured_memo": rt(),
        "recording": files(),
        "transcript": rt(),
        "meeting_url": url(),
        "google_event_id": rt(),
        "outlook_event_id": rt(),
        "kakao_event_id": rt(),
        "external_refs": rt(),
        "created_time": created_time(),
        "updated_time": last_edited_time(),
    },
    "relations": [
        {"prop": "project", "target": "project", "kind": "single"},
        {"prop": "attendees", "target": "person", "kind": "multi"},
        {"prop": "next_meeting", "target": "meeting", "kind": "single", "self": True},
        {"prop": "source_inbox", "target": "inbox", "kind": "single"},
    ],
}


# P4. Risk
DATABASES["risk"] = {
    "title": "Risk",
    "icon": "⚠️",
    "description": "프로젝트 리스크. priority = impact x probability 자동 계산.",
    "pass1_props": {
        "pk": title(),
        "name": rt(),
        "description": rt(),
        "status": select(STATUS_RISK),
        "impact": select(["High", "Medium", "Low"]),
        "probability": select(["High", "Medium", "Low"]),
        # Notion's create-DB endpoint rejects formulas that reference Select
        # props in the same request ("Type error with formula"). Created as
        # Select; convert to Formula manually in Notion UI with the expression
        # documented in README ("Risk priority formula").
        "priority": select(["High", "Medium", "Low"]),
        "response_strategy": select(["회피", "완화", "수용", "전가"]),
        "response_plan": rt(),
        "identified_date": date(),
        "target_resolve_date": date(),
        "realized_date": date(),
        "external_refs": rt(),
        "created_time": created_time(),
        "updated_time": last_edited_time(),
    },
    "relations": [
        {"prop": "project", "target": "project", "kind": "single"},
        {"prop": "owner", "target": "person", "kind": "single"},
        {"prop": "found_in_meeting", "target": "meeting", "kind": "single"},
        {"prop": "source_inbox", "target": "inbox", "kind": "single"},
    ],
}


# X1. Inbox
DATABASES["inbox"] = {
    "title": "Inbox",
    "icon": "📥",
    "description": "모든 raw 입력의 라우팅 매니페스트 + audit trail.",
    "pass1_props": {
        "pk": title(),
        "name": rt(),
        "description": rt(),
        "status": select(STATUS_INBOX),
        # Source
        "source_type": select(["telegram", "notion", "outlook", "gmail", "onedrive", "ide_session", "git", "cron", "kakao_self", "voice", "web", "manual"]),
        "source_account": rt(),
        "source_message_id": rt(),
        "source_url": url(),
        "received_at": date(),
        # Attachments
        "attachments": files(),
        "voice_file": files(),
        "image_file": files(),
        "stt_result": rt(),
        "ocr_result": rt(),
        "raw_archive_link": url(),
        # Normalized
        "normalized_text": rt(),
        "extracted_datetimes": rt(),
        "raw_person_tokens": rt(),
        "raw_company_tokens": rt(),
        # Classification
        "intent_codes": multi_select([
            "OP-TASK", "OP-DELIV", "OP-MEETING", "OP-RISK", "OP-CALENDAR",
            "OP-PROJECT", "OP-PROJ-UPDATE",
            "KN-CASE", "KN-ERROR", "KN-RESOURCE", "KN-TEMPLATE", "KN-CODE",
            "RT-SEARCH", "RT-RECOMMEND",
            "MD-COMPANY", "MD-PERSON",
            "XX-MULTI", "XX-AMBIGUOUS", "XX-NOTE", "XX-COMMAND", "XX-TRASH",
        ]),
        "confidence_score": num(),
        "classifier": rt(),
        "project_match_confidence": num(),
        # Learning
        "user_correction": rt(),
        "reprocess_count": num(),
        "learned_into_skill": checkbox(),
        "context_snapshot": rt(),
        "external_refs": rt(),
        "created_time": created_time(),
        "updated_time": last_edited_time(),
    },
    "relations": [
        {"prop": "mentioned_people", "target": "person", "kind": "multi"},
        {"prop": "mentioned_companies", "target": "company", "kind": "multi"},
        {"prop": "inferred_project", "target": "project", "kind": "single"},
        {"prop": "routed_to_projects", "target": "project", "kind": "multi"},
        {"prop": "routed_to_tasks", "target": "task", "kind": "multi"},
        {"prop": "routed_to_meetings", "target": "meeting", "kind": "multi"},
        {"prop": "routed_to_risks", "target": "risk", "kind": "multi"},
        {"prop": "routed_to_deliverables", "target": "deliverable", "kind": "multi"},
        {"prop": "routed_to_people", "target": "person", "kind": "multi"},
        {"prop": "routed_to_companies", "target": "company", "kind": "multi"},
        # Phase 2: routed_to_cases / errors / resources / templates
    ],
}


def relation_property(target_db_id, kind):
    """Build a Notion relation property spec. kind: 'single' or 'multi'.

    'multi' is a single_property relation that allows multiple targets. The
    Notion API itself doesn't distinguish single vs multi at the schema level
    for single_property — both return the same shape and Notion infers from
    usage. We keep the kind label for documentation only.
    """
    return {
        "relation": {
            "database_id": target_db_id,
            "type": "single_property",
            "single_property": {},
        }
    }
