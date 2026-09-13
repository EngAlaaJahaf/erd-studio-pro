"""AI assistant for TESTR ERD Studio Pro.

Three layers:
  1. Local heuristic assistant (works offline, no API key needed).
  2. OpenAI-compatible chat provider (OpenAI / Ollama / LM Studio / vLLM ...).
  3. Tool-use agent loop that inspects the schema, classifies subsystems and
     emits "canvas actions" that the frontend executes live on the diagram.
"""

import json
import re
import time
import uuid

import requests

from app.core import database as db
from app.core import subsystems as subsys

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
def get_ai_config():
    s = db.get_all_settings()
    return {
        "provider": s.get("ai_provider", "local"),
        "base_url": s.get("ai_base_url", "https://api.openai.com/v1").rstrip("/"),
        "api_key": s.get("ai_api_key", ""),
        "model": s.get("ai_model", "gpt-4o-mini"),
        "temperature": float(s.get("ai_temperature", "0.4") or 0.4),
    }


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------
def _schema():
    cached = db.get_cached_schema()
    if not cached:
        return {"tablesData": {}, "fkList": [], "tables": [], "fkCount": 0}
    return {
        "tablesData": cached["tablesData"],
        "fkList": cached["fkList"],
        "tables": list(cached["tablesData"].keys()),
        "fkCount": cached["fkCount"],
    }

def _subsystem_overview():
    schema = _schema()
    res = subsys.detect_subsystems(schema["tablesData"], schema["fkList"])
    saved_defs = db.get_subsystem_defs()
    if saved_defs:
        res = subsys.detect_subsystems(schema["tablesData"], schema["fkList"],
                                       subsystem_defs=list(saved_defs.values()))
    saved_map = db.get_subsystem_mappings()
    if saved_map:
        merged = dict(res["mapping"])
        for t, k in saved_map.items():
            if t in schema["tablesData"]:
                merged[t] = k
        res = subsys.detect_subsystems(
            schema["tablesData"], schema["fkList"],
            subsystem_defs=list(saved_defs.values()) if saved_defs else None,
            custom_mapping=merged)
    return res

def _is_audit(col_name):
    name = col_name.upper()
    if name in ("CREATED_BY", "CREATED_TIME", "CREATED_DATE", "CREATED_AT",
                "UPDATED_BY", "UPDATED_TIME", "UPDATED_DATE", "UPDATED_AT",
                "DELETED_BY", "DELETED_TIME", "DELETED_DATE", "DELETED_AT",
                "IS_DELETED", "VERSION_NUMBER"):
        return True
    return bool(re.match(r"^(CREATED|UPDATED|DELETED)_(BY|TIME|DATE|AT)$", name))


# ---------------------------------------------------------------------------
# Tool definitions for function calling
# ---------------------------------------------------------------------------
def _tool_defs():
    return [
        {
            "type": "function",
            "function": {
                "name": "get_schema_overview",
                "description": "Get an overview of the whole database: table count, relationships count, and the list of detected subsystems with member tables.",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_table_info",
                "description": "Get detailed info about a table: its columns (with PK/FK/audit markers), its subsystem, and incoming/outgoing foreign keys.",
                "parameters": {
                    "type": "object",
                    "properties": {"table": {"type": "string", "description": "Exact table name e.g. RAF_STUDENTS"}},
                    "required": ["table"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "find_related_tables",
                "description": "Find tables directly related to a given table via foreign keys, with the direction of the relationship.",
                "parameters": {
                    "type": "object",
                    "properties": {"table": {"type": "string"}},
                    "required": ["table"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_subsystems",
                "description": "List all detected subsystems with their member tables and counts.",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_subsystem_tables",
                "description": "Get the member tables of a specific subsystem.",
                "parameters": {
                    "type": "object",
                    "properties": {"key": {"type": "string", "description": "Subsystem key: auth, reference, notifications, academic, curriculum, students, assignments, exams, general"}},
                    "required": ["key"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_tables",
                "description": "Search tables by name substring.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"]
                }
            }
        },
        # ---- Canvas actions (executed live by the frontend) ----
        {
            "type": "function",
            "function": {
                "name": "set_theme",
                "description": "Change the visual theme of the diagram. Call this, the diagram updates instantly on the user's screen.",
                "parameters": {
                    "type": "object",
                    "properties": {"theme": {"type": "string", "enum": ["mermaid", "dark", "academic", "light"]}},
                    "required": ["theme"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "set_view_mode",
                "description": "Change which columns are shown on all tables on the canvas.",
                "parameters": {
                    "type": "object",
                    "properties": {"mode": {"type": "string", "enum": ["no-audit", "keys-only", "all-columns"]}},
                    "required": ["mode"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "apply_preset",
                "description": "Rearrange the tables on the canvas using a layout algorithm.",
                "parameters": {
                    "type": "object",
                    "properties": {"preset": {"type": "string", "enum": ["hierarchical", "grid", "cluster", "circular", "force"]}},
                    "required": ["preset"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "focus_tables",
                "description": "Select and center the view on the given tables.",
                "parameters": {
                    "type": "object",
                    "properties": {"tables": {"type": "array", "items": {"type": "string"}}},
                    "required": ["tables"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "highlight_tables",
                "description": "Temporarily highlight the given tables on the canvas.",
                "parameters": {
                    "type": "object",
                    "properties": {"tables": {"type": "array", "items": {"type": "string"}}},
                    "required": ["tables"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "clear_highlights",
                "description": "Clear all highlights.",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "hide_tables",
                "description": "Hide the given tables from the diagram.",
                "parameters": {
                    "type": "object",
                    "properties": {"tables": {"type": "array", "items": {"type": "string"}}},
                    "required": ["tables"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "show_tables",
                "description": "Reveal the given tables on the diagram.",
                "parameters": {
                    "type": "object",
                    "properties": {"tables": {"type": "array", "items": {"type": "string"}}},
                    "required": ["tables"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "show_only_subsystem",
                "description": "Filter the diagram to show only the tables of one subsystem.",
                "parameters": {
                    "type": "object",
                    "properties": {"key": {"type": "string"}},
                    "required": ["key"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "show_all_tables",
                "description": "Show every table again (clear subsystem filter).",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "color_by_subsystem",
                "description": "Color the table borders by their subsystem so the user can visually find each subsystem.",
                "parameters": {
                    "type": "object",
                    "properties": {"enabled": {"type": "boolean"}},
                    "required": ["enabled"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "hide_audit_columns",
                "description": "Hide the audit columns (created_by, updated_time, ...) on one table.",
                "parameters": {
                    "type": "object",
                    "properties": {"table": {"type": "string"}},
                    "required": ["table"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "show_all_columns",
                "description": "Show every column of one table.",
                "parameters": {
                    "type": "object",
                    "properties": {"table": {"type": "string"}},
                    "required": ["table"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "fit_view",
                "description": "Zoom and pan so the whole diagram fits the viewport.",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        },
    ]


CANVAS_TOOLS = {
    "set_theme", "set_view_mode", "apply_preset", "focus_tables",
    "highlight_tables", "clear_highlights", "hide_tables", "show_tables",
    "show_only_subsystem", "show_all_tables", "color_by_subsystem",
    "hide_audit_columns", "show_all_columns", "fit_view",
}


# ---------------------------------------------------------------------------
# Logical tool executor
# ---------------------------------------------------------------------------
def execute_logical_tool(name, args):
    schema = _schema()
    tables_data, fk_list = schema["tablesData"], schema["fkList"]
    mapping = db.get_subsystem_mappings()
    ov = _subsystem_overview()
    if not mapping:
        mapping = ov["mapping"]
    sub_by_key = {s["key"]: s for s in ov["subsystems"]}

    if name == "get_schema_overview":
        return {
            "tableCount": len(schema["tables"]),
            "fkCount": schema["fkCount"],
            "subsystems": [
                {"key": s["key"], "name_ar": s["name_ar"], "name_en": s["name_en"],
                 "tableCount": s["tableCount"]} for s in ov["subsystems"] if s["tableCount"] > 0
            ]
        }

    if name == "list_subsystems":
        return {
            "subsystems": [
                {"key": s["key"], "name_ar": s["name_ar"], "name_en": s["name_en"],
                 "description_ar": s["description_ar"], "description_en": s["description_en"],
                 "color": s["color"], "tables": s["tables"]} for s in ov["subsystems"] if s["tableCount"] > 0
            ]
        }

    if name == "get_subsystem_tables":
        key = args.get("key", "")
        s = sub_by_key.get(key) or next((x for x in ov["subsystems"] if x["key"] == key), None)
        if not s:
            return {"error": f"Unknown subsystem key: {key}", "valid_keys": [x["key"] for x in ov["subsystems"]]}
        return {"key": key, "name_ar": s["name_ar"], "tables": s["tables"]}

    if name == "get_table_info":
        table = args.get("table", "").upper()
        if table not in tables_data:
            return {"error": f"Table '{args.get('table')}' not found",
                    "suggestions": [t for t in schema["tables"] if table in t or args.get("table","").upper() in t][:8]}
        data = tables_data[table]
        child_fks = [f for f in fk_list if f["child"] == table]
        parent_fks = [f for f in fk_list if f["parent"] == table]
        cols = [{"name": c["name"], "type": c["type"],
                 "isPK": c["name"] in data["pks"],
                 "isAudit": _is_audit(c["name"])} for c in data["columns"]]
        return {
            "table": table,
            "subsystem": mapping.get(table, "general"),
            "columns": cols,
            "pks": data["pks"],
            "childFks": [{"fk": f["fk"], "parent": f["parent"], "cols": f["cols"]} for f in child_fks],
            "parentFks": [{"fk": f["fk"], "child": f["child"], "cols": f["cols"]} for f in parent_fks],
        }

    if name == "find_related_tables":
        table = args.get("table", "").upper()
        if table not in tables_data:
            return {"error": f"Table '{args.get('table')}' not found"}
        parents = [{"table": f["parent"], "fk": f["fk"], "cols": f["cols"]} for f in fk_list if f["child"] == table]
        children = [{"table": f["child"], "fk": f["fk"], "cols": f["cols"]} for f in fk_list if f["parent"] == table]
        return {"table": table, "parents": parents, "children": children}

    if name == "search_tables":
        q = args.get("query", "").upper().strip()
        matches = [t for t in schema["tables"] if not q or q in t]
        return {"query": args.get("query", ""), "matches": [{"table": t, "subsystem": mapping.get(t, "general")} for t in matches[:25]], "count": len(matches)}

    return {"error": f"Unknown logical tool: {name}"}


# ---------------------------------------------------------------------------
# OpenAI-compatible streaming + agent loop
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are the intelligent assistant embedded inside 'TESTR ERD Studio Pro', a tool for visualizing and "
    "exploring an Oracle academic database schema (TESTR) composed of tables prefixed COM_ (framework) and "
    "RAF_ (academic domain). The schema has been classified into subsystems: identity/roles/permissions (auth), "
    "settings & lookup (reference), notifications/logs (notifications), academic structure (academic), "
    "curriculum & instructors (curriculum), students & study track (students), assignments/lectures/sessions "
    "(assignments), and exams/attendance/insights (exams).\n\n"
    "You have tools available. Tools that manipulate the canvas (set_theme, set_view_mode, apply_preset, "
    "focus_tables, highlight_tables, clear_highlights, hide_tables, show_tables, show_only_subsystem, "
    "show_all_tables, color_by_subsystem, hide_audit_columns, show_all_columns, fit_view) are executed "
    "IMMEDIATELY on the user's live diagram by the application; you can chain several in one turn.\n\n"
    "Rules:\n"
    "- Reply in the SAME language as the user (Arabic if the user writes Arabic, English otherwise).\n"
    "- Use full table names (e.g. RAF_STUDENTS, COM_ROLES_AUTHORIZATION) when referencing tables.\n"
    "- Be concise but helpful. Before answering factual schema questions you MUST call the appropriate "
    "logical tool (get_table_info, find_related_tables, list_subsystems, get_subsystem_tables, search_tables, "
    "get_schema_overview) rather than guessing.\n"
    "- When the user asks for a visual change (theme, layout, focus, highlights, subsystem filtering), use the "
    "canvas tools.\n"
    "- Never invent table names or columns that tools did not return."
)


def _stream_chat_completion(messages, tools, config):
    """Yield parsed deltas from an OpenAI-compatible streamed response."""
    url = f"{config['base_url']}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['api_key']}",
    }
    body = {
        "model": config["model"],
        "messages": messages,
        "temperature": config["temperature"],
        "stream": True,
        "tools": tools or None,
    }
    with requests.post(url, headers=headers, json=body, stream=True, timeout=120) as resp:
        if resp.status_code != 200:
            try:
                detail = resp.json().get("error", {}).get("message", resp.text[:300])
            except Exception:
                detail = resp.text[:300]
            raise RuntimeError(f"Provider error {resp.status_code}: {detail}")
        for raw in resp.iter_lines(decode_unicode=True):
            if not raw:
                continue
            if raw.startswith("data:"):
                raw = raw[5:].strip()
            if raw == "[DONE]":
                break
            try:
                chunk = json.loads(raw)
            except Exception:
                continue
            choices = chunk.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            if "content" in delta and delta["content"]:
                yield {"type": "token", "content": delta["content"]}
            if delta.get("tool_calls"):
                for tc in delta["tool_calls"]:
                    yield {"type": "toolcall", "call": tc}
            finish = choices[0].get("finish_reason")
            if finish:
                yield {"type": "finish", "reason": finish}


def _assemble_tool_calls(toolcall_events):
    """Merge streamed tool-call fragments into complete calls."""
    calls = {}
    order = []
    for ev in toolcall_events:
        tc = ev["call"]
        idx = tc.get("index", 0)
        if idx not in calls:
            calls[idx] = {"id": tc.get("id") or f"call_{uuid.uuid4().hex[:8]}",
                          "name": "", "arguments": ""}
            order.append(idx)
        if tc.get("id"):
            calls[idx]["id"] = tc["id"]
        fn = tc.get("function") or {}
        if fn.get("name"):
            calls[idx]["name"] += fn["name"]
        if fn.get("arguments"):
            calls[idx]["arguments"] += fn["arguments"]
    return [calls[i] for i in order]


def _agent_loop(messages, config, history_excerpt=None):
    """Agent loop yielding event dicts. messages = list of LM messages."""
    context_note = history_excerpt or ""
    tools = _tool_defs()
    iterations = 0
    max_iter = 8

    while iterations < max_iter:
        iterations += 1
        stream_done = {"reason": None}
        toolcall_events = []
        assistant_text = ""

        try:
            for ev in _stream_chat_completion(messages, tools, config):
                if ev["type"] == "token":
                    assistant_text += ev["content"]
                    yield ev
                elif ev["type"] == "toolcall":
                    toolcall_events.append(ev)
                elif ev["type"] == "finish":
                    stream_done["reason"] = ev["reason"]
        except Exception as e:
            yield {"type": "error", "message": str(e)}
            return

        if not toolcall_events:
            yield {"type": "done"}
            return

        # Assemble tool calls
        calls = _assemble_tool_calls(toolcall_events)
        assistant_msg = {"role": "assistant", "content": assistant_text or None,
                         "tool_calls": [
                             {"id": c["id"], "type": "function",
                              "function": {"name": c["name"], "arguments": c["arguments"] or "{}"}}
                             for c in calls
                         ]}
        messages.append(assistant_msg)

        for c in calls:
            name = c["name"]
            try:
                args = json.loads(c["arguments"] or "{}")
            except Exception:
                args = {}
            yield {"type": "tool", "name": name, "status": "start"}

            if name in CANVAS_TOOLS:
                # Forward to the user's canvas; the frontend applies it live.
                yield {"type": "action", "name": name, "arguments": args}
                result = {"ok": True, "note": f"Canvas action '{name}' was applied to the diagram."}
            else:
                result = execute_logical_tool(name, args)

            yield {"type": "tool", "name": name, "status": "done"}
            messages.append({"role": "tool", "tool_call_id": c["id"],
                             "content": json.dumps(result, ensure_ascii=False)})

    yield {"type": "done", "note": "Max iterations reached"}


# ---------------------------------------------------------------------------
# Local heuristic assistant (offline fallback)
# ---------------------------------------------------------------------------
_ALIASES = {
    "طلبه|طلاب|طالب|طالب:|students?": {
        "RAF_STUDENTS", "RAF_STUDENT_STUDY_TRACK", "RAF_STUDENT_SUBJECTS",
        "RAF_STUDENT_ASSIGNMENTS", "RAF_STUDENT_EXAMS"}
}

_CONCEPT_MAP = [
    (re.compile(r"امتحان|اختبار|exams?", re.I), ["RAF_EXAMS", "RAF_STUDENT_EXAMS"]),
    (re.compile(r"تكليف|واجب|تسليم|assignments?", re.I), ["RAF_ASSIGNMENTS", "RAF_STUDENT_ASSIGNMENTS"]),
    (re.compile(r"محاضره|محاضرة|lectures?", re.I), ["RAF_LECTURES"]),
    (re.compile(r"حضور|غياب|attendance", re.I), ["RAF_ATTENDANCE"]),
    (re.compile(r"مستخدم|حساب|accounts?|users?", re.I), ["COM_ACCOUNTS", "COM_USERS_ROLES"]),
    (re.compile(r"دور|صلاحيه|صلاحية|roles?|permissions?", re.I), ["COM_ROLES_AUTHORIZATION", "COM_USER_AUTHORIZATIONS"]),
    (re.compile(r"جامعه|جامعة|universit", re.I), ["RAF_UNIVERSITIES"]),
    (re.compile(r"كليه|كلية|college", re.I), ["RAF_COLLEGES"]),
    (re.compile(r"قسم|department", re.I), ["RAF_DEPARTMENTS"]),
    (re.compile(r"مقرر|ماده|مادة|موضوع|subject|course", re.I), ["RAF_SUBJECTS_MASTER", "RAF_UNIVERSITY_SUBJECTS"]),
    (re.compile(r"منهج|خطه|خطة|curricul", re.I), ["RAF_CURRICULUM_MAP", "RAF_CURRICULUM_BATCHES"]),
    (re.compile(r"مدرس|مدرس:|instructor", re.I), ["RAF_INSTRUCTORS", "RAF_INSTRUCTOR_SUBJECTS"]),
    (re.compile(r"مجموعه|مجموعة|شعبه|شعبة|groups?", re.I), ["RAF_GROUPS"]),
]

_SUBSYS_LOCAL_ORDER = ["auth", "reference", "notifications", "academic", "facilities",
                       "curriculum", "students", "assignments", "exams"]

_SUBSYS_ALIASES = {
    "auth": ["صلاحي", "دور", "أدوار", "ادوار", "هوية", "حسابات", "مستخدم", "role", "permission", "security", "authoriz"],
    "reference": ["إعداد", "اعداد", "قوائم", "مرجع", "lookup", "setting", "reference", "قائمة"],
    "notifications": ["إشعار", "اشعار", "إخطار", "اخطار", "سجلات", "الأخطاء", "مراقبة", "notification", "log", "monitor"],
    "academic": ["هياكل", "هيكل", "جامعات", "جامعة", "كليات", "أقسام", "اقسام", "فصول", "أكاديمي", "اكاديمي", "academic", "university", "program"],
    "facilities": ["مرافق", "حجوزات", "حجز", "جلسات", "جلسة", "قاعات", "facility", "facilit", "booking", "book", "session"],
    "curriculum": ["مناهج", "منهج", "خطة", "خطه", "مقررات", "curriculum", "curric"],
    "students": ["طلبة", "طلاب", "طالب", "student"],
    "assignments": ["تكليفات", "تكليف", "واجبات", "محاضرات", "assignment", "lecture", "task"],
    "exams": ["امتحانات", "امتحان", "الامتحان", "حضور", "غياب", "نتائج", "توصيات", "exam", "attendance", "grade", "result", "insight"],
}

def _detect_subsystem_key(text):
    low = text.lower()
    for key in _SUBSYS_LOCAL_ORDER:
        for alias in _SUBSYS_ALIASES.get(key, []):
            if alias in low:
                return key
    return None

def _is_arabic(text):
    return bool(re.search(r"[\u0600-\u06FF]", text))

def _find_tables(text, schema_tables):
    """Return a list of known table names referenced in the text."""
    found = []
    upper = text.upper()
    for t in sorted(schema_tables, key=len, reverse=True):
        if t in upper:
            found.append(t)
    if not found:
        for rx, tables in _CONCEPT_MAP:
            if rx.search(text):
                found = list(tables)
                break
    return found


def _extract_theme(text):
    t = text.lower()
    if "داكن" in t or "ليلي" in t or "dark" in t:
        return "dark"
    if "فاتح" in t or "ناصع" in t or "light" in t or "ابيض" in t:
        return "light"
    if "زمردي" in t or "اخضر" in t or "أخضر" in t or "academic" in t or "اكاديمي" in t:
        return "academic"
    if "كلاسيكي" in t or "بنفسجي" in t or "mermaid" in t or "افتراضي" in t:
        return "mermaid"
    return None


def _extract_preset(text):
    t = text.lower()
    if "شبك" in t or "grid" in t:
        return "grid"
    if "هرمي" in t or "شجره" in t or "شجرة" in t or "hierarchical" in t or "tree" in t:
        return "hierarchical"
    if "مجموعات" in t or "cluster" in t:
        return "cluster"
    if "دائري" in t or "circular" in t or "دائره" in t or "دائرة" in t:
        return "circular"
    if "فيزيائي" in t or "force" in t or "فيزي" in t:
        return "force"
    return None


def _extract_view_mode(text):
    t = text.lower()
    if "مفاتيح" in t or "keys" in t or "فقط" in t and "مفاتيح" in t:
        return "keys-only"
    if "كل" in t and ("حقول" in t or "col" in t) or "all" in t and ("col" in t):
        return "all-columns"
    if "تدقيق" in t or "audit" in t or "بدون" in t:
        return "no-audit"
    return None


def local_respond(messages, context):
    """Heuristic assistant -> yields action events + a final reply."""
    schema = _schema()
    tables_data, fk_list = schema["tablesData"], schema["fkList"]
    ov = _subsystem_overview()
    mapping = db.get_subsystem_mappings() or ov["mapping"]
    sub_by_key = {s["key"]: s for s in ov["subsystems"]}

    last = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last = m.get("content") or ""
            break
    text = last
    ar = _is_arabic(text)
    actions = []

    def say(full):
        yield {"type": "token", "content": full}
        yield {"type": "done"}

    low = text.lower()
    t_tables = _find_tables(text, schema["tables"])

    # 1) Global visual commands ------------------------------------------
    theme = _extract_theme(text)
    if theme and ("ثيم" in low or "مظهر" in low or "theme" in low or "داكن" in low
                  or "فاتح" in low or "dark" in low or "light" in low or "زمرد" in low
                  or "اخضر" in low or "أخضر" in low or "كلاسيكي" in low or "بنفسجي" in low):
        actions.append({"name": "set_theme", "arguments": {"theme": theme}})

    preset = _extract_preset(text)
    if preset and ("رتب" in low or "ترتيب" in low or "layout" in low or "شبك" in low
                   or "هرمي" in low or "دائري" in low or "فيزي" in low or "grid" in low
                   or "cluster" in low or "circular" in low or "tree" in low or "طبّق" in low
                   or "طبق" in low or "وزع" in low):
        actions.append({"name": "apply_preset", "arguments": {"preset": preset}})

    vmode = _extract_view_mode(text)
    if vmode and ("عرض" in low or "mode" in low or "مفاتيح" in low or "تدقيق" in low or "حقول" in low):
        actions.append({"name": "set_view_mode", "arguments": {"mode": vmode}})

    if "ملاءمة" in low or "عرض الكل" in low or "مناسب للعرض" in low or "fit" in low or "انظر الكل" in low:
        actions.append({"name": "fit_view", "arguments": {}})

    # 2) Explicit subsystem filter ("اعرض فقط نظام X") -------------------
    filter_intent = any(k in low for k in ["اعرض فقط", "اظهر فقط", "أظهر فقط", "عرض فقط",
                                           "فقط جداول", "فقط نظام", "تصفية", "فلترة",
                                           "show only", "filter"])
    subkey = _detect_subsystem_key(text) if filter_intent else None
    if subkey:
        actions.append({"name": "show_only_subsystem", "arguments": {"key": subkey}})

    # 3) Highlight / focus ------------------------------------------------
    if ("ابرز" in low or "أبرز" in low or "highlight" in low or "سلط الضوء" in low) and t_tables:
        actions.append({"name": "highlight_tables", "arguments": {"tables": t_tables}})
    elif ("انتقل" in low or "اذهب" in low or "توجه" in low or "ركز" in low or "focus" in low
          or "مركز" in low) and t_tables and not actions:
        actions.append({"name": "focus_tables", "arguments": {"tables": t_tables}})

    # 4) Hide / show tables -----------------------------------------------
    if t_tables and ("اخف" in low or "أخف" in low or "hide" in low or "غط" in low):
        actions.append({"name": "hide_tables", "arguments": {"tables": t_tables}})
    elif any(k in low for k in ["جميع الجداول", "كل الجداول", "اظهار الكل", "اظهار جميع",
                                "أظهر الكل", "أظهر جميع", "استعادة الكل", "كل شء",
                                "show all tables", "show all", "restore all"]):
        actions.append({"name": "show_all_tables", "arguments": {}})
    elif t_tables and (("اظهر" in low or "أظهر" in low or "استعد" in low or "عرض" in low
                        and "جدول" in low) or "show" in low) and not actions:
        actions.append({"name": "show_tables", "arguments": {"tables": t_tables}})

    # 5) Color by subsystem -----------------------------------------------
    if "لون" in low or "تلوين" in low or "الوان" in low or "ألوان" in low or "color" in low:
        enabled = not ("دون" in low or "بدون" in low or "false" in low or "لا" in low)
        actions.append({"name": "color_by_subsystem", "arguments": {"enabled": enabled}})

    # If we did visual work, summarize and stop ---------------------------
    if actions:
        for a in actions:
            yield {"type": "action", "name": a["name"], "arguments": a.get("arguments", {})}
        names = ", ".join(a["name"] for a in actions)
        reply = (ar and f"✅ تم تنفيذ {len(actions)} إجراء على المخطط: {names}." or
                 f"✅ Executed {len(actions)} action(s) on the diagram: {names}.")
        yield from say(reply)
        return

    # 6) Relationships answer ---------------------------------------------
    if t_tables and ("علاقات" in low or "ارتباط" in low or "مترابط" in low or "fk" in low
                     or "foreign" in low or "مرتبط" in low or "من يرتبط" in low
                     or "relation" in low or "relat" in low or "connect" in low
                     or "reference" in low or "links" in low):
        tbl = t_tables[0]
        info = execute_logical_tool("find_related_tables", {"table": tbl})
        parents = info.get("parents", [])
        children = info.get("children", [])
        lines = []
        if ar:
            lines.append(f"🔗 علاقات {tbl}:")
            for p in parents:
                lines.append(f"  • أب (parent): {p['table']} عبر {p['fk']} ({p['cols']})")
            for c in children:
                lines.append(f"  • ابن (child): {c['table']} عبر {c['fk']} ({c['cols']})")
            if not lines[1:]:
                lines.append("  (لا توجد علاقات مباشرة)")
        else:
            lines.append(f"🔗 Relationships for {tbl}:")
            for p in parents:
                lines.append(f"  • Parent: {p['table']} via {p['fk']} ({p['cols']})")
            for c in children:
                lines.append(f"  • Child: {c['table']} via {c['fk']} ({c['cols']})")
            if not lines[1:]:
                lines.append("  (no direct relationships)")
        yield from say("\n".join(lines))
        return

    # 7) Table info answer -------------------------------------------------
    if t_tables and ("معلومات" in low or "ما هو" in low or "ماهو" in low or "اعطي" in low
                     or "صف " in low or "اطلع" in low or "describe" in low or "info" in low
                     or "ايش يحتوي" in low or "يحتوي" in low or "what is" in low
                     or "about " in low or "tell me about" in low):
        tbl = t_tables[0]
        info = execute_logical_tool("get_table_info", {"table": tbl})
        if "error" in info:
            yield from say("❌ " + str(info.get("error")))
            return
        sub_name = sub_by_key.get(info.get("subsystem", "general"), {}).get("name_ar" if ar else "name_en", info.get("subsystem"))
        cols = info["columns"]
        audit_n = sum(1 for c in cols if c["isAudit"])
        pks = info["pks"]
        if ar:
            reply = (f"📋 معلومات جدول {tbl}\n"
                     f"• النظام الفرعي: {sub_name}\n"
                     f"• عدد الأعمدة: {len(cols)} (منها {audit_n} عمود تدقيق)\n"
                     f"• المفاتيح الأساسية: {', '.join(pks) if pks else '—'}\n"
                     f"• المفاتيح الأجنبية الواردة: {len(info['childFks'])}, الصادرة: {len(info['parentFks'])}")
        else:
            reply = (f"📋 Info for {tbl}\n"
                     f"• Subsystem: {sub_name}\n"
                     f"• Columns: {len(cols)} (audit: {audit_n})\n"
                     f"• PKs: {', '.join(pks) if pks else '—'}\n"
                     f"• Incoming FKs: {len(info['childFks'])}, outgoing: {len(info['parentFks'])}")
        yield from say(reply)
        return

    # 8) Subsystem listing ---------------------------------------------------
    if ("نظام" in low or "انظمة" in low or "أنظمة" in low or "تصنيف" in low or "صنف" in low
            or "subsystem" in low or "classif" in low or "مجالات" in low):
        lines = []
        if ar:
            lines.append("🧩 الأنظمة الفرعية المكتشفة في قاعدة البيانات:")
        else:
            lines.append("🧩 Detected subsystems:")
        for s in ov["subsystems"]:
            if s["tableCount"] == 0:
                continue
            name = s["name_ar"] if ar else s["name_en"]
            desc = s["description_ar"] if ar else s["description_en"]
            lines.append(f"• {name} [{s['key']}] — {s['tableCount']} جداول")
            lines.append(f"   {desc}")
        yield from say("\n".join(lines))
        return

    # 9) Fallback help -------------------------------------------------------
    overview = execute_logical_tool("get_schema_overview", {})
    n_subs = sum(1 for s in overview.get("subsystems", []) if s["tableCount"] > 0)
    if ar:
        reply = (
            "أهلاً! أنا مساعد TESTR الذكي 🤖\n"
            "يمكنني مساعدتك بـ:\n"
            "• تصنيف الجداول والنظر في الأنظمة الفرعية (الصلاحيات، التكليفات، الامتحانات...).\n"
            "• الإجابة عن الجداول والأعمدة والعلاقات.\n"
            "• تنفيذ أوامر على المخطط: تغيير الثيم، الترتيب، الإبراز، الإخفاء، التصفية حسب النظام.\n\n"
            f"القاعدة الحالية: {overview['tableCount']} جدول، {overview['fkCount']} علاقة في {n_subs} أنظمة فرعية.\n"
            "جرّب: «أبرز جداول نظام التكليفات» أو «غيّر الثيم إلى داكن» أو «ما علاقات COM_ACCOUNTS؟»"
        )
    else:
        reply = (
            "Hi! I'm the TESTR smart assistant 🤖\n"
            "I can help you with:\n"
            "• Classifying tables & exploring subsystems (permissions, assignments, exams...).\n"
            "• Answering questions about tables, columns and relationships.\n"
            "• Executing diagram commands: theme, layout, highlight, hide, subsystem filtering.\n\n"
            f"Current schema: {overview['tableCount']} tables, {overview['fkCount']} relationships in {n_subs} subsystems.\n"
            "Try: «highlight the assignments subsystem» or «switch theme to dark» or «relations of COM_ACCOUNTS?»"
        )
    yield from say(reply)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def chat_agent(messages, context):
    """Yield event dicts. messages: LM-style message list (with latest user msg)."""
    config = get_ai_config()
    provider = config.get("provider", "local")

    last_user = ""
    for m in reversed(messages):
        if m.get("role") == "user" and isinstance(m.get("content"), str):
            last_user = m["content"]
            break

    reply_parts = []

    def wrap(gen):
        for ev in gen:
            if ev.get("type") == "token":
                reply_parts.append(ev.get("content") or "")
            yield ev
        if last_user and reply_parts:
            try:
                db.add_chat_message("user", last_user)
                db.add_chat_message("assistant", "".join(reply_parts))
            except Exception:
                pass

    if provider == "local" or not config.get("api_key"):
        yield from wrap(local_respond(messages, context))
        return

    # Optionally pre-warm with a lightweight summary the agent can trust
    excerpt = context or ""
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in messages[-24:]:
        if isinstance(m.get("content"), str):
            msgs.append(m)
    yield from wrap(_agent_loop(msgs, config, history_excerpt=excerpt))


def test_provider(config=None):
    config = config or get_ai_config()
    if config.get("provider") == "local" or not config.get("api_key"):
        return {"success": True, "mode": "local", "message": "Local assistant (works offline, no API key needed)"}
    try:
        url = f"{config['base_url']}/chat/completions"
        resp = requests.post(url, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['api_key']}",
        }, json={
            "model": config["model"],
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 5,
        }, timeout=30)
        if resp.status_code == 200:
            return {"success": True, "mode": "remote", "model": config["model"],
                    "message": f"Provider OK ({config['base_url']})"}
        try:
            detail = resp.json().get("error", {}).get("message", resp.text[:200])
        except Exception:
            detail = resp.text[:200]
        return {"success": False, "mode": "remote", "error": f"HTTP {resp.status_code}: {detail}"}
    except Exception as e:
        return {"success": False, "mode": "remote", "error": str(e)}