"""Data Dictionary (.xlsx) importer for ERD Studio.

Each Excel sheet represents one table in the classic ERD Data Dictionary
layout (title row, bilingual header rows, then column rows):

    col1: Field name      col2: Caption / prompt
    col3: Data type       col4: Length / Size
    col5: PK              col6: M (not null)
    col7: U (unique)      col8: I (index)
    col9: FK              col10: References  e.g. "RAF_COLLEGES(COLLEGE_ID)"
    col11: check          col13: Default Value
    col14: Description

Builds the unified tablesData / fkList model used across the app.
"""
import re

import openpyxl

CHECK_MARKS = {"✓", "√", "v", "y", "yes", "1"}
NONE_MARKS = {"-", "--", "", "nan", "none", "null"}
HEADER_COL0 = {"#", "م", "t", "序号"}
HEADER_C1 = {"field name", "fieldname", "column name", "إسم الحقل", "اسم الحقل", "أعمدة"}
INDEX_SHEETS = {"index", "فهرس", "قائمة", "list", "contents"}

_TABLE_NAME_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:[(\-\u2013]?\s*(.+?)\s*[)\u2013]?)?\s*$")
_REF_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)")
_TYPE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)")


def _norm(v):
    if v is None:
        return ""
    return str(v).strip()


def _is_check(v):
    return _norm(v).lower() in CHECK_MARKS


def _cell(row, idx):
    try:
        v = row[idx]
    except (IndexError, TypeError):
        return ""
    return _norm(v)


def _table_identity(title_row_value, sheet_name):
    raw = _norm(title_row_value) or _norm(sheet_name)
    m = _TABLE_NAME_RE.match(raw)
    if not m:
        return None, raw
    return m.group(1), m.group(2) or raw


def _parse_size(size_v):
    s = _norm(size_v)
    if not s or s.lower() in {"-", "nan", "none"}:
        return ""
    return s


def _build_type(base_v, size_v):
    base = _norm(base_v)
    if not base:
        return "VARCHAR2"
    m = _TYPE_RE.match(base)
    if m:
        base = m.group(1)
    base = base.upper()
    if not base.startswith(("NUMBER", "VARCHAR2", "NVARCHAR2", "CHAR", "BINARY_FLOAT",
                            "RAW", "DECIMAL", "NUMERIC", "REAL", "FLOAT", "TIMESTAMP",
                            "INT", "INTEGER", "BIGINT", "SMALLINT", "TINYINT", "MEDIUMINT",
                            "BIT", "SERIAL", "BLOB", "CLOB", "TEXT", "DATE", "TIME",
                            "DATETIME", "INTERVAL", "BOOL", "BOOLEAN", "JSON", "GEOMETRY",
                            "MONEY", "SMALLMONEY", "UNIQUEIDENTIFIER", "UROWID", "ROWID",
                            "IDENTITY", "BIGSERIAL", "DOUBLE", "UUID", "ENUM", "SET")):
        return base
    size = _parse_size(size_v)
    if size:
        return f"{base}({size})"
    return base


# ---------------------------------------------------------------------------
# Audit columns: used by the "generate / remove audit columns" import option.
# Mirrors the frontend AUDIT_COLUMNS_SET + isAuditColumn() rules.
# ---------------------------------------------------------------------------
AUDIT_ADD_COLS = [
    {"name": "CREATED_AT", "type": "TIMESTAMP", "nullable": False,
     "caption": "تاريخ الإنشاء", "unique": False, "indexed": False,
     "check": "", "default_value": "", "description": ""},
    {"name": "CREATED_BY", "type": "VARCHAR2(60)", "nullable": True,
     "caption": "أنشأه", "unique": False, "indexed": False,
     "check": "", "default_value": "", "description": ""},
    {"name": "UPDATED_AT", "type": "TIMESTAMP", "nullable": True,
     "caption": "تاريخ آخر تعديل", "unique": False, "indexed": False,
     "check": "", "default_value": "", "description": ""},
    {"name": "UPDATED_BY", "type": "VARCHAR2(60)", "nullable": True,
     "caption": "عدّله", "unique": False, "indexed": False,
     "check": "", "default_value": "", "description": ""},
]

_AUDIT_RE = re.compile(
    r"^(CREATED|UPDATED|DELETED)_(BY|TIME|DATE|AT)$"
    r"|^IS_DELETED$"
    r"|^VERSION_NUMBER$"
    r"|^(LAST_ACTIVITY|LAST_LOGIN|LAST_IP_ADDRESS|DEVICE_FINGERPRINT|LOGIN_COUNT)$"
    r"|^(EMAIL_VERIFICATION_TOKEN|EMAIL_VERIFICATION_EXPIRY)$"
    r"|^(PASSWORD_RESET_CODE|RESET_CODE_EXPIRY|RESET_CODE_USED_AT)$"
    r"|^(SCAN_IP_ADDRESS|SCAN_LATITUDE|SCAN_LONGITUDE)$"
    r"|^(EXCUSE_REVIEWED_BY|EXCUSE_REVIEW_NOTES|REVIEWED_BY|REVIEWED_AT|REVIEW_NOTES)$",
    re.IGNORECASE,
)


def is_audit_column(name: str) -> bool:
    return bool(_AUDIT_RE.match(name.strip().upper()))


def apply_audit_policy(tables_data: dict, policy: str) -> list:
    """Apply the audit-columns option to a merged schema model.

    policy:
      "keep"   -> unchanged
      "add"    -> append the standard audit columns to every table lacking them
      "remove" -> strip every column that matches the audit rules

    Returns a list of human-readable notes describing what was done.
    """
    notes = []
    if policy not in ("add", "remove"):
        return notes
    for tname, data in tables_data.items():
        cols = data.get("columns") or []
        keep = []
        any_audit = False
        for c in cols:
            name = c.get("name", "")
            if (policy == "remove") and is_audit_column(name):
                any_audit = True
                continue
            keep.append(c)
            if is_audit_column(name):
                any_audit = True
        if policy == "add":
            names = {c.get("name", "") for c in keep}
            if not any_audit:
                for ac in AUDIT_ADD_COLS:
                    if ac["name"] not in names:
                        keep.append(dict(ac))
                notes.append(f"أُضيفت أعمدة تدقيق إلى جدول «{tname}»")
        else:
            if any_audit:
                notes.append(f"حُذفت أعمدة التدقيق من جدول «{tname}»")
        data["columns"] = keep
        data["pks"] = [p for p in (data.get("pks") or []) if p in {c.get("name") for c in keep}]
    return notes


def _build_fk_list(raw_fks, tables_data, seen=None):
    if seen is None:
        seen = set()
    fk_list = []
    dangling = []
    for f in raw_fks:
        if f["child"] not in tables_data:
            continue
        if f["parent"] not in tables_data:
            dangling.append(f"{f['child']}.{f['child_col']} -> {f['parent']}({f['parent_col']})")
            continue
        key = (f["child"], f["parent"], f["child_cols"][0])
        if key in seen:
            continue
        seen.add(key)
        fk_list.append({
            "child": f["child"],
            "parent": f["parent"],
            "fk": f"FK_{f['child']}_{f['parent']}_{f['child_col']}"[:60],
            "cols": ", ".join(f["child_cols"]),
        })
    return fk_list, dangling


def parse_xlsx(data: bytes) -> dict:
    """Parse an .xlsx Data Dictionary workbook.

    Returns {tablesData, fkList, rawFks, summary} for ingest_schema.
    """
    wb = _load(data)
    tables_data = {}
    raw_fks = []
    warnings = []
    captions = {}

    for ws in wb.worksheets:
        if ws.title.strip().lower() in INDEX_SHEETS:
            continue
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue

        header_ix = None
        for i, r in enumerate(rows[:8]):
            c0 = _norm(r[0] if r and len(r) else "")
            c1 = _norm(r[1] if r and len(r) > 1 else "")
            if c0 in HEADER_COL0 or c1.lower() in HEADER_C1:
                header_ix = i
                break
        if header_ix is None:
            warnings.append(f"ورقة «{ws.title}»: لم يتم العثور على رأس الأعمدة وتُجاهلت")
            continue

        title_row = rows[header_ix - 1] if header_ix > 0 else None
        title_val = title_row[0] if title_row and len(title_row) else ""
        table_name, table_caption = _table_identity(title_val, ws.title)
        if not table_name:
            table_name = re.sub(r"[^A-Za-z0-9_]", "_", ws.title)
            if not table_name:
                warnings.append(f"ورقة «{ws.title}»: اسم جدول غير صالح وتُجاهلت")
                continue
        table_name = table_name.upper()
        if table_name == "INDEX" or table_name.startswith("INDEX"):
            continue
        if table_name in tables_data:
            warnings.append(f"جدول «{table_name}» مكرر (ورقة «{ws.title}») — سيبقى الأول")
            continue

        columns = []
        pks = []
        for r in rows[header_ix + 1:]:
            name = _cell(r, 1)
            if not name:
                continue
            if _norm(r[0] if r and len(r) else "").lower() in HEADER_COL0 or name.lower() in HEADER_C1:
                continue
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
                warnings.append(f"جدول «{table_name}»: عمود «{name}» باسم غير صالح وتُجاهل")
                continue
            dtype = _build_type(_cell(r, 3), _cell(r, 4))
            mandatory = _is_check(_cell(r, 6))
            pkip = _is_check(_cell(r, 5))
            unique = _is_check(_cell(r, 7))
            indexed = _is_check(_cell(r, 8))
            col = {
                "name": name,
                "type": dtype,
                "nullable": not mandatory,
                "caption": _cell(r, 2),
                "unique": unique,
                "indexed": indexed,
                "check": _cell(r, 11),
                "default_value": _cell(r, 13) if _norm(_cell(r, 13)) not in {"-", ""} else "",
                "description": _cell(r, 14),
            }
            if pkip:
                pks.append(name)
            columns.append(col)

            refs = _REF_RE.findall(_cell(r, 10))
            for parent, parent_col in refs:
                raw_fks.append({
                    "child": table_name,
                    "parent": parent.upper(),
                    "fk": None,
                    "child_cols": [name],
                    "parent_cols": [parent_col.upper()],
                    "child_col": name,
                    "parent_col": parent_col.upper(),
                })

        if not columns:
            warnings.append(f"جدول «{table_name}» (ورقة «{ws.title}»): لا أعمدة صالحة وتُجاهل")
            continue

        tables_data[table_name] = {"columns": columns, "pks": pks}
        captions[table_name] = table_caption or ws.title or table_name

    fk_list, dangling = _build_fk_list(raw_fks, tables_data)

    if dangling:
        warnings.append(f"{len(dangling)} علاقة تشير لجداول غير موجودة في الملف وتُجاهلت (مثال: {dangling[0]})")

    return {
        "tablesData": tables_data,
        "fkList": fk_list,
        "rawFks": raw_fks,
        "summary": {
            "tables": len(tables_data),
            "fks": len(fk_list),
            "dangling": dangling,
            "warnings": warnings,
            "captions": captions,
            "sheetCount": len(wb.worksheets),
        },
    }


def _load(data: bytes):
    import io
    return openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)