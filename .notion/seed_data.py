"""Initial seed data for SAP Module + Business Area masters.

setup.py runs pass 3 to insert these. Idempotent: rows are matched by `pk`
and skipped if already present.
"""

# ---------- SAP Module (M3) ----------
# pk = standard SAP code; spec calls out 19 entries.

SAP_MODULES = [
    # Finance
    {"pk": "FI", "name": "재무회계", "english_name": "Financial Accounting", "category": "Finance", "skill_level": "Expert"},
    {"pk": "CO", "name": "관리회계", "english_name": "Controlling", "category": "Finance", "skill_level": "Expert"},
    {"pk": "FICO", "name": "재무·관리회계 통합", "english_name": "Financial & Controlling (combined)", "category": "Finance", "skill_level": "Expert", "aliases": "FI/CO"},
    # Logistics
    {"pk": "MM", "name": "자재관리", "english_name": "Materials Management", "category": "Logistics", "skill_level": "Advanced"},
    {"pk": "SD", "name": "영업·유통", "english_name": "Sales & Distribution", "category": "Logistics", "skill_level": "Advanced"},
    {"pk": "SD-LE", "name": "영업·물류실행 통합", "english_name": "SD & Logistics Execution (combined)", "category": "Logistics", "skill_level": "Advanced", "aliases": "SD/LE"},
    {"pk": "PP", "name": "생산계획", "english_name": "Production Planning", "category": "Logistics", "skill_level": "Intermediate"},
    {"pk": "PS", "name": "프로젝트시스템", "english_name": "Project System", "category": "Logistics", "skill_level": "Intermediate"},
    {"pk": "QM", "name": "품질관리", "english_name": "Quality Management", "category": "Logistics", "skill_level": "Intermediate"},
    {"pk": "PM", "name": "설비관리", "english_name": "Plant Maintenance", "category": "Logistics", "skill_level": "Novice"},
    {"pk": "WM", "name": "창고관리", "english_name": "Warehouse Management", "category": "Logistics", "skill_level": "Intermediate"},
    # HR
    {"pk": "HCM", "name": "인적자원관리", "english_name": "Human Capital Management", "category": "HR", "skill_level": "Novice", "aliases": "HR / SuccessFactors"},
    {"pk": "SuccessFactors", "name": "SuccessFactors", "english_name": "SAP SuccessFactors (HXM cloud)", "category": "HR", "skill_level": "Novice"},
    # Technology
    {"pk": "Basis", "name": "베이시스", "english_name": "SAP Basis (admin)", "category": "Technology", "skill_level": "Intermediate"},
    {"pk": "ABAP", "name": "ABAP 개발", "english_name": "Advanced Business Application Programming", "category": "Technology", "skill_level": "Advanced"},
    {"pk": "PI", "name": "프로세스 통합", "english_name": "Process Integration / PO", "category": "Technology", "skill_level": "Intermediate", "aliases": "XI / PO"},
    {"pk": "BW", "name": "비즈니스 웨어하우스", "english_name": "Business Warehouse", "category": "Technology", "skill_level": "Novice"},
    # Cross
    {"pk": "S4-Core", "name": "S/4HANA Core", "english_name": "SAP S/4HANA Core platform", "category": "Cross", "skill_level": "Advanced"},
    {"pk": "Ariba", "name": "Ariba 구매 클라우드", "english_name": "SAP Ariba", "category": "Cross", "skill_level": "Novice"},
]


# ---------- Business Area (M4) ----------
# Two-tier: parent categories (BA-XXX) and subcategories (BA-XXX-YYY).
# Pass 3 creates parents first then children with parent_area relation.

# Parent categories
BUSINESS_AREA_PARENTS = [
    {"pk": "BA-FIN", "name": "Finance", "description": "재무·회계 영역 부모 카테고리"},
    {"pk": "BA-COS", "name": "Costing", "description": "원가·코스팅 영역 부모 카테고리"},
    {"pk": "BA-PUR", "name": "Purchasing", "description": "구매·조달 영역 부모 카테고리"},
    {"pk": "BA-SAL", "name": "Sales", "description": "영업·판매 영역 부모 카테고리"},
    {"pk": "BA-PRD", "name": "Production", "description": "생산·제조 영역 부모 카테고리"},
    {"pk": "BA-INT", "name": "Integration", "description": "인터페이스·통합 영역 부모 카테고리"},
]

# Subcategories — parent is referenced by parent_pk
BUSINESS_AREA_CHILDREN = [
    # Finance
    {"pk": "BA-FIN-FX", "name": "외화환산", "parent_pk": "BA-FIN"},
    {"pk": "BA-FIN-AR", "name": "매출채권", "parent_pk": "BA-FIN"},
    {"pk": "BA-FIN-AP", "name": "매입채무", "parent_pk": "BA-FIN"},
    {"pk": "BA-FIN-AA", "name": "자산회계", "parent_pk": "BA-FIN"},
    {"pk": "BA-FIN-GL", "name": "일반회계", "parent_pk": "BA-FIN"},
    # Costing
    {"pk": "BA-COS-IMP", "name": "수입부대비", "parent_pk": "BA-COS"},
    {"pk": "BA-COS-ALC", "name": "원가배부", "parent_pk": "BA-COS"},
    {"pk": "BA-COS-PRC", "name": "제품원가", "parent_pk": "BA-COS"},
    # Purchasing
    {"pk": "BA-PUR-GEN", "name": "일반구매", "parent_pk": "BA-PUR"},
    {"pk": "BA-PUR-SUB", "name": "외주구매", "parent_pk": "BA-PUR"},
    {"pk": "BA-PUR-MM", "name": "자재마스터", "parent_pk": "BA-PUR"},
    # Sales
    {"pk": "BA-SAL-ORD", "name": "수주관리", "parent_pk": "BA-SAL"},
    {"pk": "BA-SAL-SHP", "name": "출하", "parent_pk": "BA-SAL"},
    {"pk": "BA-SAL-BIL", "name": "청구", "parent_pk": "BA-SAL"},
    # Production
    {"pk": "BA-PRD-PLN", "name": "생산계획", "parent_pk": "BA-PRD"},
    {"pk": "BA-PRD-WO", "name": "작업지시", "parent_pk": "BA-PRD"},
    {"pk": "BA-PRD-BOM", "name": "BOM", "parent_pk": "BA-PRD"},
    # Integration
    {"pk": "BA-INT-IF", "name": "인터페이스", "parent_pk": "BA-INT"},
    {"pk": "BA-INT-EDI", "name": "EDI", "parent_pk": "BA-INT"},
    {"pk": "BA-INT-IDoc", "name": "IDoc", "parent_pk": "BA-INT"},
]
