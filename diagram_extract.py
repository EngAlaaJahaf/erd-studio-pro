"""Local, offline heuristic extractors that turn a text section into a basic
sequence / activity / use case spec. The result is never as good as the LLM
path (diagram_llm.py) but it works with zero configuration.

Each extractor returns (spec, warnings) where spec is a plain dict matching the
shapes consumed by diagram_specs.normalize_spec.
"""

import re
from collections import OrderedDict

from document_sections import _looks_like_title

ROLE_AR = [
    "المستخدم", "الطالب", "الطالبة", "الدكتور", "الأستاذ", "الأستاذة",
    "الموظف", "الإداري", "المشرف", "المحاضر", "المرشد", "العميل",
    "المريض", "النظام", "المنسق", "أمين السر", "المكتب", "الإدارة",
]
ROLE_EN = [
    "user", "student", "doctor", "teacher", "employee", "admin", "client",
    "system", "manager", "supervisor", "patient", "officer", "staff",
]

ROLE_RE_AR = re.compile(r"\b(?:" + "|".join(re.escape(r) for r in ROLE_AR) + r")\b")
ROLE_RE_EN = re.compile(r"\b(?:" + "|".join(re.escape(r) for r in ROLE_EN) + r")\b", re.I)

COND_AR = re.compile(r"(?:إذا كان|إذا|في حال|عندما|أما إذا|في حالة|بشرط|إلا إذا|متى)", re.I)
COND_EN = re.compile(r"\b(?:if|when|unless|should|in case|otherwise|while|until)\b", re.I)

ACTION_VERBS_AR = [
    "تسجيل", "إنشاء", "إضافة", "حذف", "تعديل", "عرض", "استعلام", "بحث",
    "طباعة", "تقرير", "إرسال", "استلام", "اعتماد", "مراجعة", "موافقة",
    "رفض", "تعيين", "توزيع", "متابعة", "إلغاء", "تحويل", "تحديث", "حجز",
    "تمكين", "تعطيل", "نسخ", "تصدير", "إدخال", "تسليم", "منح", "إصدار", "تحقق",
]
ACTION_VERBS_EN = [
    "register", "create", "add", "delete", "edit", "update", "view", "search",
    "print", "report", "send", "receive", "approve", "review", "assign",
    "book", "cancel", "enable", "disable", "export", "import", "submit",
]
VERB_AR_SET = set(ACTION_VERBS_AR)
VERB_EN_SET = set(ACTION_VERBS_EN)

BRACKET_LINE_RE = re.compile(r"^[-*•]\s*(.+)$")
NUM_LINE_RE = re.compile(r"^(?:\d+(?:\.\d+)*|[\u0660-\u0669]+)[\-\)\.]?\s*(.+)$")


def _lines(text):
    out = []
    for ln in (text or "").splitlines():
        if _looks_like_title(ln):
            continue  # skip headings inside a section body
        ln = ln.rstrip(".;،:")
        ln = (BRACKET_LINE_RE.sub(r"\1", ln) or NUM_LINE_RE.sub(r"\1", ln) or ln).strip()
        if len(ln) > 1:
            out.append(ln)
    return out


def _roles_in(text):
    roles = []
    for m in re.finditer(ROLE_RE_AR, text):
        if m.group(0) not in roles:
            roles.append(m.group(0))
    for m in re.finditer(ROLE_RE_EN, text):
        r = m.group(0)
        if r not in roles:
            roles.append(r)
    return roles


def _default_roles():
    return ["المستخدم", "النظام"]


# ---------------------------------------------------------------------------
# Sequence
# ---------------------------------------------------------------------------
def extract_sequence(text):
    warnings = []
    lines = _lines(text)
    roles = OrderedDict()
    steps = []
    for ln in lines:
        found = _roles_in(ln)
        for r in found:
            roles.setdefault(r)
        steps.append((ln, found))
    if not roles:
        roles = OrderedDict((r, None) for r in _default_roles())
        warnings.append("لم نتعرف على أدوار واضحة؛ استخدمنا المستخدم/النظام. (No clear actors found; used user/system.)")

    participants = list(roles.keys())
    messages, used_pairs = [], set()
    for ln, found in steps[:16]:
        if len(ln) > 140:
            ln = ln[:140] + "…"
        if len(found) >= 2:
            fm, to = found[0], found[1]
        elif len(found) == 1:
            fm, to = found[0], participants[-1]
        else:
            fm, to = participants[0], participants[-1]
        if (fm, to) in used_pairs:
            # still allow, but avoid infinite identical garbage
            pass
        used_pairs.add((fm, to))
        messages.append({"from": fm, "to": to, "label": ln})
    if not messages:
        messages = [{"from": participants[0], "to": participants[-1], "label": "استدعاء الخدمة"}]
        warnings.append("لم نستخلص خطوات صريحة؛ نتج تسلسل افتراضي. (No explicit steps found.)")
    spec = {"type": "sequence", "participants": participants, "messages": messages}
    return spec, warnings


# ---------------------------------------------------------------------------
# Activity
# ---------------------------------------------------------------------------
def extract_activity(text):
    warnings = []
    lines = _lines(text)[:15]
    if not lines:
        raise ValueError("لا يوجد نص كافٍ لاستخلاص مخطط النشاط. (No text to analyze.)")
    nodes = [{"id": "start", "type": "start", "label": "ابدأ"}]
    edges = []
    prev = "start"
    idx = 0
    for ln in lines:
        is_cond = bool(COND_AR.search(ln) or COND_EN.search(ln))
        idx += 1
        nid = f"n{idx}"
        ntype = "decision" if is_cond else "action"
        label = ln[:120]
        if not (label in [n["label"] for n in nodes]):
            nodes.append({"id": nid, "type": ntype, "label": label})
            edges.append({"from": prev, "to": nid, "label": ""})
            prev = nid
    nodes.append({"id": "end", "type": "end", "label": "نهاية"})
    edges.append({"from": prev, "to": "end", "label": ""})
    # annotate decision branches with نعم/لا to a following action when possible
    ids = [n["id"] for n in nodes]
    for e in list(edges):
        if any(n["id"] == e["from"] and n["type"] == "decision" for n in nodes):
            out_i = ids.index(e["to"]) if e["to"] in ids else -1
            e["label"] = "نعم / yes" if out_i > 0 else ""
    if not any(n["type"] == "decision" for n in nodes):
        warnings.append("لم نجد شروطاً واضحة (إذا/عندما...). (No explicit conditions found.)")
    if len(nodes) <= 2:
        warnings.append("النص قصير جداً؛ المخطط أولي. (Very short text; preliminary diagram.)")
    return {"type": "activity", "nodes": nodes, "edges": edges}, warnings


# ---------------------------------------------------------------------------
# Use case
# ---------------------------------------------------------------------------
def _verb_phrases(text, lang="ar"):
    """Extract action clauses by locating nominal/verb stems and cutting the
    surrounding sentence into a short use-case label (dictionary based)."""
    verbs = VERB_AR_SET if lang == "ar" else VERB_EN_SET
    found = []
    for verb in verbs:
        # Arabic has no \b for letters: require the stem NOT to be glued to a
        # preceding Arabic letter (so "التسليمات" won't match stem "تسليم").
        pattern = r"(?<![\u0600-\u06FF])" + re.escape(verb)
        for m in re.finditer(pattern, text, re.I):
            clause = text[m.start():]
            for s in ("\n", "؛", ".", "،", "!", "؟"):
                i = clause.find(s)
                if i != -1 and i < 90:
                    clause = clause[:i]
                    break
            clause = clause[:90].strip(" :،;،\n\ufeff")
            if len(clause) >= 3 and clause not in found:
                found.append(clause)
        if len(found) >= 10:
            break
    return found


def extract_usecase(text):
    warnings = []
    lines = _lines(text)
    actors = OrderedDict()
    for ln in lines:
        for r in _roles_in(ln):
            actors.setdefault(r.lower().capitalize(), r)

    usecase_map = OrderedDict()
    for ph in _verb_phrases(text, "ar"):
        usecase_map.setdefault(ph, None)
    for ph in _verb_phrases(text, "en"):
        usecase_map.setdefault(ph, None)
    if not usecase_map:
        for ln in lines[:8]:
            usecase_map.setdefault(ln[:70], None)
        warnings.append("لم نستخلص حالات استخدام صريحة؛ استخدمنا أسطر النص. (No explicit use cases.)")
        if not len(usecase_map):
            raise ValueError("تعذر استخلاص حالات استخدام. (Cannot extract use cases.)")

    uc_ids = {name: f"u{i + 1}" for i, name in enumerate(usecase_map.keys())}
    actor_ids = {name: f"a{i + 1}" for i, name in enumerate(actors.keys())}
    actor_names = list(actors.keys())

    associations = []
    for i, uc in enumerate(usecase_map.keys()):
        roles_in_uc = _roles_in(uc)
        actor = actor_names[i % len(actor_names)]
        if roles_in_uc:
            for r in reversed(roles_in_uc):
                cand = r.lower().capitalize()
                if cand in actor_ids:
                    actor = cand
                    break
        associations.append({"actor": actor_ids[actor], "usecase": uc_ids[uc]})

    spec = {
        "type": "usecase",
        "system": "النظام (System)",
        "actors": [{"id": actor_ids[n], "name": n} for n in actor_names],
        "usecases": [{"id": uc_ids[n], "name": n} for n in usecase_map],
        "associations": associations,
        "includes": [],
        "extends": [],
    }
    if len(actors) <= 1:
        warnings.append("جهة فاعلة واحدة فقط؛ اعتمدنا توزيعاً مباشراً. (Single actor; direct associations.)")
    return spec, warnings


def extract(text, diagram_type):
    """Dispatch to the right local extractor. Returns (spec, warnings)."""
    diagram_type = str(diagram_type or "").strip().lower()
    if diagram_type == "sequence":
        return extract_sequence(text)
    if diagram_type == "activity":
        return extract_activity(text)
    if diagram_type == "usecase":
        return extract_usecase(text)
    raise ValueError(f"unsupported diagram type: {diagram_type}")