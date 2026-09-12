"""Generic, schema-agnostic subsystem classifier.

Works for ANY database family (Oracle, MySQL, PostgreSQL, SQLite, ...) and any
set of table names. The classifier is NOT hard-coded to a specific schema:

1. A broad multi-domain token dictionary maps common English word fragments
   (user, order, booking, patient, ...) to generic subsystem domains.
2. Tables that match nothing (or tie) are grouped by FK-graph label
   propagation, so tightly related tables always end up in one subsystem.
3. Names/colors can be overridden by LLM-provided subsystem definitions
   (see ai_classify.py) or by the user; unknown clusters keep auto names.
"""

from collections import defaultdict

# ---------------------------------------------------------------------------
# Generic starter taxonomy (broad, multi-domain, schema-agnostic)
# ---------------------------------------------------------------------------
DEFAULT_DOMAINS = [
    {
        "key": "auth",
        "name_ar": "الهوية والدخول والصلاحيات",
        "name_en": "Identity, Access & Permissions",
        "description_ar": "المستخدمون والحسابات والأدوار والصلاحيات وجلسات الدخول.",
        "description_en": "Users, accounts, roles, permissions and login sessions.",
        "color": "#2563eb",
        "tokens": ["authentication", "authorization", "credential", "permission",
                   "security_group", "password", "account", "login", "user_role",
                   "username", "privilege", "user_session", "sso", "profile",
                   "user", "role", "session", "access", "auth"],
    },
    {
        "key": "reference",
        "name_ar": "الإعدادات والقوائم المرجعية",
        "name_en": "Settings & Reference Lists",
        "description_ar": "القوائم المرجعية والإعدادات العامة وقوائم النظام الثابتة.",
        "description_en": "Lookup lists, global settings and static system data.",
        "color": "#7c3aed",
        "tokens": ["lookup", "setting", "parameter", "configuration", "reference",
                   "dictionary", "category", "menu", "enum", "definition",
                   "constant", "country", "currency", "city", "region"],
    },
    {
        "key": "notifications",
        "name_ar": "الإشعارات والسجلات والمراقبة",
        "name_en": "Notifications, Logs & Monitoring",
        "description_ar": "الإشعارات وقوالبها وسجلات الأخطاء وأنشطة النظام.",
        "description_en": "Notifications, templates, error logs and system activity.",
        "color": "#f59e0b",
        "tokens": ["notification", "notify", "alert", "error_log", "audit_log",
                   "event_log", "activity_log", "monitor", "trace", "alarm",
                   "webhook", "log", "audit"],
    },
    {
        "key": "academic",
        "name_ar": "الهيكل الأكاديمي",
        "name_en": "Academic Structure",
        "description_ar": "الجامعات والكليات والأقسام والبرامج والمستويات والفترات الزمنية.",
        "description_en": "Universities, colleges, departments, programs, levels and time slots.",
        "color": "#059669",
        "tokens": ["university", "college", "faculty", "department", "program",
                   "level", "semester", "term", "academic_week", "classroom",
                   "time_slot", "timetable", "campus", "period", "academic",
                   "institute"],
    },
    {
        "key": "curriculum",
        "name_ar": "المناهج والمقررات",
        "name_en": "Curriculum & Courses",
        "description_ar": "المقررات والمناهج والمدرسون وربطهم بالمقررات.",
        "description_en": "Courses, syllabi, instructors and their subject mapping.",
        "color": "#ea580c",
        "tokens": ["subject", "course", "curriculum", "syllabus", "batch",
                   "instructor", "teacher", "lesson"],
    },
    {
        "key": "students",
        "name_ar": "سجل الطلبة",
        "name_en": "Students",
        "description_ar": "البيانات الرئيسية للطلبة ومسارهم الدراسي.",
        "description_en": "Core student records and study enrollment.",
        "color": "#0d9488",
        "tokens": ["student", "enrollment", "registrant", "learner", "pupil"],
    },
    {
        "key": "assignments",
        "name_ar": "التكليفات والمحاضرات",
        "name_en": "Assignments & Lectures",
        "description_ar": "التكليفات وتسليمات الطلبة والمحاضرات.",
        "description_en": "Assignments, submissions and lectures.",
        "color": "#db2777",
        "tokens": ["assignment", "homework", "submission", "lecture", "task",
                   "exercise"],
    },
    {
        "key": "facilities",
        "name_ar": "المرافق والحجوزات",
        "name_en": "Facilities & Bookings",
        "description_ar": "حجوزات القاعات والمرافق والموارد والجلسات.",
        "description_en": "Room/venue bookings, facilities, resources and sessions.",
        "color": "#0891b2",
        "tokens": ["booking", "reservation", "classroom_booking", "facility",
                   "resource", "venue", "slot"],
    },
    {
        "key": "exams",
        "name_ar": "الامتحانات والتقييم والحضور",
        "name_en": "Exams, Assessment & Attendance",
        "description_ar": "الامتحانات والنتائج والتقييم والحضور والغياب.",
        "description_en": "Exams, results, grading, attendance and absence.",
        "color": "#dc2626",
        "tokens": ["exam", "examination", "assessment", "grading", "attendance",
                   "absence", "presence", "question_paper", "question", "result",
                   "score", "mark", "grade", "quiz", "evaluation"],
    },
    {
        "key": "commerce",
        "name_ar": "التجارة والطلبات",
        "name_en": "Commerce & Orders",
        "description_ar": "العملاء والطلبات والمنتجات والمخزون وسلاسل التوريد.",
        "description_en": "Customers, orders, products, inventory and supply chain.",
        "color": "#f97316",
        "tokens": ["customer", "order_item", "order", "cart", "product",
                   "inventory", "stock", "warehouse", "supplier", "shipment",
                   "discount", "checkout", "purchase", "catalog", "category_order"],
    },
    {
        "key": "payments",
        "name_ar": "المدفوعات والمالية",
        "name_en": "Payments & Finance",
        "description_ar": "المدفوعات والفواتير والمعاملات المالية.",
        "description_en": "Payments, invoices, transactions and financial records.",
        "color": "#16a34a",
        "tokens": ["payment", "invoice", "transaction", "refund", "billing",
                   "wallet", "ledger", "receipt", "charge", "fee", "bank_account"],
    },
    {
        "key": "hr",
        "name_ar": "الموارد البشرية",
        "name_en": "Human Resources",
        "description_ar": "الموظفون والعقود والرواتب والإجازات.",
        "description_en": "Employees, contracts, payroll and leaves.",
        "color": "#6366f1",
        "tokens": ["employee", "staff", "payroll", "salary", "timesheet",
                   "applicant", "job_candidate", "job_posting", "leave",
                   "vacation", "contract_emp"],
    },
    {
        "key": "healthcare",
        "name_ar": "الرعاية الصحية",
        "name_en": "Healthcare",
        "description_ar": "المرضى والأطباء والمواعيد والوصفات والفحوصات.",
        "description_en": "Patients, doctors, appointments, prescriptions and labs.",
        "color": "#ec4899",
        "tokens": ["patient", "physician", "appointment_slot", "prescription",
                   "diagnosis", "medical_record", "clinic", "treatment",
                   "pharmacy", "lab_test", "doctor", "nurse"],
    },
    {
        "key": "logistics",
        "name_ar": "الخدمات اللوجستية والأسطول",
        "name_en": "Logistics & Fleet",
        "description_ar": "الشحنات والتوصيل والمركبات والسائقون والمسارات.",
        "description_en": "Shipments, deliveries, vehicles, drivers and routes.",
        "color": "#84cc16",
        "tokens": ["shipment", "courier", "delivery", "vehicle", "driver",
                   "route", "fleet", "journey", "trip_log", "fuel_refill"],
    },
    {
        "key": "content",
        "name_ar": "المحتوى والوسائط",
        "name_en": "Content & Media",
        "description_ar": "المقالات والمشاركات والتعليقات وملفات الوسائط.",
        "description_en": "Articles, posts, comments and media files.",
        "color": "#a855f7",
        "tokens": ["article", "blog_post", "post", "comment", "media", "image",
                   "video", "thumbnail", "attachment", "author_content"],
    },
    {
        "key": "communication",
        "name_ar": "التواصل والدردشة",
        "name_en": "Communication & Chat",
        "description_ar": "رسائل الدردشة والمحادثات والإشعارات المرسلة.",
        "description_en": "Chat messages, conversations and outbound contact.",
        "color": "#0ea5e9",
        "tokens": ["conversation", "chat", "message_log", "message", "thread",
                   "forum", "contact"],
    },
    {
        "key": "general",
        "name_ar": "جداول عامة",
        "name_en": "General Tables",
        "description_ar": "جداول لا تنتمي بقوة لنظام فرعي محدد.",
        "description_en": "Tables not strongly tied to any subsystem.",
        "color": "#64748b",
        "tokens": [],
    },
]

_AUTO_PALETTE = ["#0d9488", "#ea580c", "#f59e0b", "#16a34a", "#a855f7",
                 "#0891b2", "#f97316", "#6366f1", "#84cc16", "#ec4899",
                 "#dc2626", "#059669"]


def _build_token_index(domains):
    index = defaultdict(list)
    for d in domains:
        if d["key"] == "general":
            continue
        for tok in d.get("tokens", []):
            index[tok].append(d["key"])
    # "member" fallback: add tokens of everything? no, keep index explicit.
    return index


# ---------------------------------------------------------------------------
# Keyword scoring
# ---------------------------------------------------------------------------
def _name_matches(table_name, token_index):
    """Return list of (token_len, token_pos, key) for matched tokens."""
    low = table_name.lower()
    matches = []
    for token, keys in token_index.items():
        pos = low.find(token)
        if pos >= 0:
            for key in keys:
                matches.append((len(token), pos, key, token))
    return matches


def _pick_best_key(matches):
    """Choose the best subsystem key: longest token, then smallest position
    (most specific / trailing part), else None if exact tie."""
    if not matches:
        return None
    best = max(matches, key=lambda m: (m[0], -m[1]))
    ties = [m for m in matches if m[0] == best[0] and m[1] == best[1]]
    if len(ties) > 1:
        return None
    return best[2]


# ---------------------------------------------------------------------------
# FK graph helpers
# ---------------------------------------------------------------------------
def _neighbors(table, fk_list):
    nbrs = set()
    for f in fk_list:
        if f["parent"] == table:
            nbrs.add(f["child"])
        if f["child"] == table:
            nbrs.add(f["parent"])
    return nbrs


def _connected_components(tables, fk_list):
    adj = {t: _neighbors(t, fk_list) for t in tables}
    seen = set()
    comps = []
    for t in tables:
        if t in seen:
            continue
        stack = [t]
        comp = set()
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            comp.add(n)
            for nb in adj.get(n, set()):
                if nb not in seen and nb in adj:
                    stack.append(nb)
        comps.append(comp)
    return comps


# ---------------------------------------------------------------------------
# Main classifier
# ---------------------------------------------------------------------------
def detect_subsystems(tables_data, fk_list, subsystem_defs=None, custom_mapping=None):
    """Classify every table in tables_data into a subsystem.

    subsystem_defs: optional list of subsystem definitions (from the LLM or the
                    user). Keys not present fall back to generic domains.
    custom_mapping: optional {table: key} provided by a stronger classifier
                    (e.g. LLM). Any table missing from it is filled locally.

    Returns: {"mapping": {table: key}, "subsystems": [...defs with tables/count]}
    """
    tables = list(tables_data.keys())

    # Collect definitions: LLM/user defs + generic taxonomy for missing keys
    defs = {}
    for d in subsystem_defs or []:
        defs[d["key"]] = _normalize_def(d)
    for d in DEFAULT_DOMAINS:
        defs.setdefault(d["key"], dict(d))
    token_index = _build_token_index(list(defs.values()))

    assignment = {}
    if custom_mapping:
        for t in tables:
            k = custom_mapping.get(t)
            if k and k in defs:
                assignment[t] = k

    # Pass 1: keyword scoring for remaining tables
    pending = [t for t in tables if t not in assignment]
    ambiguous = []
    for t in pending:
        matches = _name_matches(t, token_index)
        key = _pick_best_key(matches)
        if key:
            assignment[t] = key
        else:
            ambiguous.append(t)

    # Pass 2: FK-label propagation for ambiguous tables
    guard = 0
    while ambiguous and guard < 60:
        guard += 1
        nxt = []
        progressed = False
        for t in ambiguous:
            votes = defaultdict(int)
            for n in _neighbors(t, fk_list):
                if n in assignment:
                    votes[assignment[n]] += 1
            if votes:
                winner = max(votes.items(), key=lambda kv: (kv[1], kv[0]))[0]
                assignment[t] = winner
                progressed = True
            else:
                nxt.append(t)
        ambiguous = nxt
        if not progressed:
            break

    # Pass 3: component-name fallback for whole connected components
    leftovers = [t for t in ambiguous if t not in assignment]
    if leftovers:
        comps = _connected_components(leftovers, fk_list)
        for comp in comps:
            # count neighbor labels across the whole graph for the component
            votes = defaultdict(int)
            for t in comp:
                for n in _neighbors(t, fk_list):
                    if n in assignment:
                        votes[assignment[n]] += 1
            if votes:
                winner = max(votes.items(), key=lambda kv: (kv[1], kv[0]))[0]
                for t in comp:
                    assignment[t] = winner
            else:
                for t in comp:
                    assignment[t] = "general"

    for t in tables:
        assignment.setdefault(t, "general")

    # Build subsystem objects enriched with members
    members = defaultdict(list)
    for t, key in assignment.items():
        members[key].append(t)
    for key in members:
        members[key].sort()

    subsystems = []
    used = set()
    for d in defs.values():
        lst = members.get(d["key"], [])
        subsystems.append({**d, "tables": lst, "tableCount": len(lst)})
        used.add(d["key"])
    # Auto-derived defs for any detected key lacking a definition
    for key in sorted(members):
        if key in used:
            continue
        pal = _AUTO_PALETTE[len(subsystems) % len(_AUTO_PALETTE)]
        subsystems.append({
            "key": key,
            "name_ar": f"وحدة {key}",
            "name_en": f"Module {key}",
            "description_ar": "مجموعة جداول مرتبطة تم اكتشافها تلقائياً.",
            "description_en": "Automatically detected group of related tables.",
            "color": pal,
            "tables": members[key],
            "tableCount": len(members[key]),
        })
        used.add(key)

    return {
        "mapping": assignment,
        "subsystems": subsystems,
    }


def _normalize_def(d):
    d = dict(d)
    d.setdefault("name_ar", d.get("name_en", d["key"]))
    d.setdefault("name_en", d.get("name_ar", d["key"]))
    d.setdefault("description_ar", "")
    d.setdefault("description_en", "")
    d.setdefault("color", _AUTO_PALETTE[0])
    d.setdefault("tokens", [])
    return d