"""Schema Linter & Best-Practices Audit Service.
Performs deep architectural inspections on relational database schemas:
1. Missing Primary Key (CRITICAL)
2. FK Datatype Mismatch (CRITICAL)
3. Orphan / Isolated Tables (WARNING)
4. Missing Index on Foreign Key Columns (WARNING / PERFORMANCE)
5. Overly Long Identifiers (INFO)
6. Nullable PK Columns (WARNING)
"""

import re
from typing import Dict, List, Any, Optional

ORACLE_RESERVED_WORDS = {
    "ACCESS", "ADD", "ALL", "ALTER", "AND", "ANY", "AS", "ASC", "AUDIT", "BETWEEN",
    "BY", "CHAR", "CHECK", "CLUSTER", "COLUMN", "COMMENT", "COMPRESS", "CONNECT",
    "CREATE", "CURRENT", "DATE", "DECIMAL", "DEFAULT", "DELETE", "DESC", "DISTINCT",
    "DROP", "ELSE", "EXCLUSIVE", "EXISTS", "FILE", "FLOAT", "FOR", "FROM", "GRANT",
    "GROUP", "HAVING", "IDENTIFIED", "IMMEDIATE", "IN", "INCREMENT", "INDEX",
    "INITIAL", "INSERT", "INTEGER", "INTERSECT", "INTO", "IS", "LEVEL", "LIKE",
    "LOCK", "LONG", "MAXEXTENTS", "MINUS", "MLSLABEL", "MODE", "MODIFY", "NOAUDIT",
    "NOCOMPRESS", "NOT", "NOWAIT", "NULL", "NUMBER", "OF", "OFFLINE", "ON",
    "ONLINE", "OPTION", "OR", "ORDER", "PCTFREE", "PRIOR", "PRIVILEGES", "PUBLIC",
    "RAW", "RENAME", "RESOURCE", "REVOKE", "ROW", "ROWID", "ROWNUM", "ROWS",
    "SELECT", "SESSION", "SET", "SHARE", "SIZE", "SMALLINT", "START", "SUCCESSFUL",
    "SYNONYM", "SYSDATE", "TABLE", "THEN", "TO", "TRIGGER", "UID", "UNION",
    "UNIQUE", "UPDATE", "USER", "VALIDATE", "VALUES", "VARCHAR", "VARCHAR2",
    "VIEW", "WHENEVER", "WHERE", "WITH"
}


def _normalize_type(t: str) -> str:
    """Normalize data type string for comparison (e.g. 'VARCHAR2 ( 50 )' -> 'varchar2(50)')."""
    if not t:
        return ""
    s = re.sub(r"\s+", "", str(t).lower())
    # Standardize aliases
    s = re.sub(r"^int\b", "integer", s)
    s = re.sub(r"^varchar\b", "varchar2", s)
    s = re.sub(r"^numeric\b", "number", s)
    return s


def _extract_base_type(t: str) -> str:
    """Extract base type ignoring size parameters, e.g. 'varchar2(50)' -> 'varchar2'."""
    s = _normalize_type(t)
    m = re.match(r"^([a-z0-9_]+)", s)
    return m.group(1) if m else s


def audit_schema(tables_data: Dict[str, Any], fk_list: List[Dict[str, Any]], dialect: str = "oracle") -> Dict[str, Any]:
    """Run comprehensive schema linting and best-practices audit."""
    findings: List[Dict[str, Any]] = []
    
    table_names = set(tables_data.keys())
    fk_incoming_count: Dict[str, int] = {t: 0 for t in table_names}
    fk_outgoing_count: Dict[str, int] = {t: 0 for t in table_names}

    # Count incoming and outgoing FKs per table
    for fk in fk_list:
        c = fk.get("child")
        p = fk.get("parent")
        if c in fk_outgoing_count:
            fk_outgoing_count[c] += 1
        if p in fk_incoming_count:
            fk_incoming_count[p] += 1

    # 1. Per-table inspections
    for tname, tdata in tables_data.items():
        cols = tdata.get("columns") or []
        pks = tdata.get("pks") or [c["name"] for c in cols if c.get("pk")]
        col_map = {c["name"].upper(): c for c in cols if "name" in c}

        # Rule 1: Missing Primary Key (CRITICAL)
        if not pks:
            first_col = cols[0]["name"] if cols else "ID"
            findings.append({
                "ruleId": "MISSING_PK",
                "severity": "CRITICAL",
                "table": tname,
                "column": None,
                "title_ar": f"الجدول «{tname}» لا يحتوي على مفتاح أساسي (Primary Key)",
                "title_en": f"Table '{tname}' has no Primary Key",
                "description_ar": "يؤدي غياب المفتاح الأساسي إلى تدهور أداء الاستعلامات، صعوبة تعقب السجلات الفريدة، وفشل الربط المرجعي وأنظمة الـ ORM.",
                "description_en": "Missing PK causes query degradation, inability to uniquely identify rows, and breaks ORMs / replication.",
                "impact": "Data Integrity & Performance",
                "fixSql": f'ALTER TABLE "{tname}" ADD CONSTRAINT "PK_{tname}" PRIMARY KEY ("{first_col}");'
            })

        # Rule 2: Nullable PK Column (WARNING)
        for pk_col_name in pks:
            col_info = col_map.get(pk_col_name.upper())
            if col_info and col_info.get("nullable") is True:
                findings.append({
                    "ruleId": "NULLABLE_PK",
                    "severity": "WARNING",
                    "table": tname,
                    "column": pk_col_name,
                    "title_ar": f"حقل المفتاح الأساسي «{pk_col_name}» في «{tname}» يقبل قيماً فارغة (Nullable)",
                    "title_en": f"Primary Key column '{pk_col_name}' in '{tname}' is nullable",
                    "description_ar": "أعمدة المفتاح الأساسي يجب أن تكون معرفة كـ NOT NULL بشكل صريح وفقاً للمعايير القياسية لمنع تضارب البيانات.",
                    "description_en": "Primary key columns must strictly be defined as NOT NULL.",
                    "impact": "Integrity Violation",
                    "fixSql": f'ALTER TABLE "{tname}" MODIFY ("{pk_col_name}" NOT NULL);'
                })

        # Rule 3: Orphan / Isolated Table (WARNING)
        total_rels = fk_incoming_count.get(tname, 0) + fk_outgoing_count.get(tname, 0)
        if total_rels == 0 and len(tables_data) > 1:
            findings.append({
                "ruleId": "ORPHAN_TABLE",
                "severity": "WARNING",
                "table": tname,
                "column": None,
                "title_ar": f"الجدول «{tname}» معزول ولا يرتبط بأي علاقة خارجية",
                "title_en": f"Table '{tname}' is isolated with no incoming or outgoing relations",
                "description_ar": "الجدول غير مرتبط بأي جدول آخر في المخطط. قد يكون جدول إعدادات ثابتة (Lookup) أو جدولاً قديماً مهجوراً يجب ربطه أو إزالته.",
                "description_en": "Table has 0 relationships. It may be a lookup table or an obsolete unlinked entity.",
                "impact": "Architecture Cleanliness",
                "fixSql": f'-- تحقق من حاجة الجدول «{tname}» لعلاقات خارجية، أو وثقه كجدول Lookup مستقل'
            })

        # Rule 4: Overly Long Identifiers (INFO)
        if len(tname) > 30:
            findings.append({
                "ruleId": "LONG_IDENTIFIER",
                "severity": "INFO",
                "table": tname,
                "column": None,
                "title_ar": f"اسم الجدول «{tname}» يتجاوز 30 حرفاً ({len(tname)} حرف)",
                "title_en": f"Table name '{tname}' exceeds 30 characters ({len(tname)} chars)",
                "description_ar": "أسماء الكائنات التي تتجاوز 30 حرفاً قد تسبب عدم توافق مع إصدارات Oracle 12.1 والإصدارات الأقدم وبعض أدوات BI.",
                "description_en": "Identifiers exceeding 30 characters may cause incompatibility on older Oracle versions and BI tools.",
                "impact": "Portability",
                "fixSql": f'-- يفضل اختصار الاسم: "{tname[:30]}"'
            })

        # Rule 5: Reserved SQL words used as column names (WARNING)
        for c in cols:
            cname = c.get("name", "")
            if cname.upper() in ORACLE_RESERVED_WORDS:
                findings.append({
                    "ruleId": "RESERVED_KEYWORD",
                    "severity": "WARNING",
                    "table": tname,
                    "column": cname,
                    "title_ar": f"الحقل «{cname}» في جدول «{tname}» يحمل كلمة محجوزة في SQL",
                    "title_en": f"Column '{cname}' in table '{tname}' is a reserved SQL keyword",
                    "description_ar": f"استخدام الكلمات المحجوزة مثل ({cname}) يتطلب وضع علامات التنصيص دائماً وقد يسبب أخطاء غير متوقعة في الاستعلامات والإجراءات المخزنة.",
                    "description_en": f"Reserved keywords require quoted identifiers and often break ORMs and query builders.",
                    "impact": "Code Reliability",
                    "fixSql": f'ALTER TABLE "{tname}" RENAME COLUMN "{cname}" TO "{cname}_VAL";'
                })

    # 2. Relationship & Foreign Key inspections
    for fk in fk_list:
        child_tbl = fk.get("child")
        parent_tbl = fk.get("parent")
        child_col_name = fk.get("cols") or fk.get("childCol") or ""
        if not child_col_name and isinstance(fk.get("columns"), list) and fk.get("columns"):
            child_col_name = fk["columns"][0]
        parent_col_name = fk.get("parentCol") or ""
        if not parent_col_name and isinstance(fk.get("parentColumns"), list) and fk.get("parentColumns"):
            parent_col_name = fk["parentColumns"][0]
        fk_name = fk.get("name") or f"FK_{child_tbl}_{parent_tbl}"

        if not child_tbl or not parent_tbl or child_tbl not in tables_data or parent_tbl not in tables_data:
            continue

        child_data = tables_data[child_tbl]
        parent_data = tables_data[parent_tbl]
        child_cols = {c["name"].upper(): c for c in child_data.get("columns", []) if "name" in c}
        parent_cols = {c["name"].upper(): c for c in parent_data.get("columns", []) if "name" in c}
        parent_pks = parent_data.get("pks") or [c["name"] for c in parent_data.get("columns", []) if c.get("pk")]

        # If parent_col_name is not specified, default to parent's first PK
        if not parent_col_name and parent_pks:
            parent_col_name = parent_pks[0]

        child_col_info = child_cols.get(child_col_name.upper())
        parent_col_info = parent_cols.get(parent_col_name.upper())

        # Rule 6: Mismatched FK Data Types (CRITICAL)
        if child_col_info and parent_col_info:
            c_type = child_col_info.get("type", "")
            p_type = parent_col_info.get("type", "")
            c_norm = _normalize_type(c_type)
            p_norm = _normalize_type(p_type)
            c_base = _extract_base_type(c_type)
            p_base = _extract_base_type(p_type)

            if c_base != p_base or (c_norm != p_norm and "number" in c_base and c_norm and p_norm):
                findings.append({
                    "ruleId": "FK_DATATYPE_MISMATCH",
                    "severity": "CRITICAL",
                    "table": child_tbl,
                    "column": child_col_name,
                    "title_ar": f"عدم تطابق نوع المفتاح الأجنبي «{child_tbl}.{child_col_name}» ({c_type}) مع أصله «{parent_tbl}.{parent_col_name}» ({p_type})",
                    "title_en": f"FK datatype mismatch: '{child_tbl}.{child_col_name}' ({c_type}) vs '{parent_tbl}.{parent_col_name}' ({p_type})",
                    "description_ar": "اختلاف نوع أو طول حقل المفتاح الخارجي عن المفتاح الأساسي المقابل يسبب فشل إنشاء القيد في بعض قواعد البيانات وبطء شديد في عمليات الربط (JOIN).",
                    "description_en": "Mismatched data types prevent constraint creation or cause implicit casting that ruins JOIN performance.",
                    "impact": "Data Integrity & Performance",
                    "fixSql": f'ALTER TABLE "{child_tbl}" MODIFY ("{child_col_name}" {p_type});'
                })

        # Rule 7: Missing Index on Foreign Key Columns (WARNING / PERFORMANCE)
        # Foreign key columns must be indexed in Oracle to prevent full table locks on parent updates/deletes
        # We check if this column is the first PK column (which already has an index)
        is_pk_indexed = (child_col_name.upper() in [pk.upper() for pk in (child_data.get("pks") or [])])
        if not is_pk_indexed and child_col_name:
            idx_name = f"IDX_{child_tbl[:16]}_{child_col_name[:10]}"
            findings.append({
                "ruleId": "MISSING_FK_INDEX",
                "severity": "WARNING",
                "table": child_tbl,
                "column": child_col_name,
                "title_ar": f"غياب الفهرس عن حقل المفتاح الأجنبي «{child_tbl}.{child_col_name}»",
                "title_en": f"Missing index on Foreign Key column '{child_tbl}.{child_col_name}'",
                "description_ar": "عدم وجود فهرس على أعمدة المفاتيح الأجنبية في Oracle يؤدي إلى إقفال كامل للجدول (Share Lock) عند حذف أو تعديل صفوف من الجدول الأب.",
                "description_en": "Unindexed foreign keys in Oracle cause full table share-locks on child tables when parent rows are modified/deleted.",
                "impact": "Database Concurrency & Locking",
                "fixSql": f'CREATE INDEX "{idx_name}" ON "{child_tbl}" ("{child_col_name}");'
            })

    # Sort findings by severity: CRITICAL first, then WARNING, then INFO
    severity_order = {"CRITICAL": 1, "WARNING": 2, "INFO": 3}
    findings.sort(key=lambda x: (severity_order.get(x["severity"], 99), x["table"]))

    # Calculate overall health score (0 - 100)
    critical_count = sum(1 for f in findings if f["severity"] == "CRITICAL")
    warning_count = sum(1 for f in findings if f["severity"] == "WARNING")
    info_count = sum(1 for f in findings if f["severity"] == "INFO")

    # Score deduction: Critical = -15 pts, Warning = -5 pts, Info = -1 pt
    base_score = 100
    deductions = (critical_count * 15) + (warning_count * 5) + (info_count * 1)
    health_score = max(0, min(100, base_score - deductions))

    # Grade
    if health_score >= 95:
        grade = "A+"
        rating_ar = "معمارية ممتازة"
        rating_en = "Excellent Architecture"
    elif health_score >= 85:
        grade = "A"
        rating_ar = "معمارية جيدة جداً"
        rating_en = "Very Good Architecture"
    elif health_score >= 75:
        grade = "B"
        rating_ar = "معمارية جيدة مع بعض التحذيرات"
        rating_en = "Good Architecture with Warnings"
    elif health_score >= 60:
        grade = "C"
        rating_ar = "معمارية مقبولة تتطلب تحسينات"
        rating_en = "Acceptable, Needs Improvement"
    elif health_score >= 40:
        grade = "D"
        rating_ar = "مشاكل معمارية حرجة"
        rating_en = "Critical Architectural Issues"
    else:
        grade = "F"
        rating_ar = "معمارية غير مطابقة للمواصفات"
        rating_en = "Non-compliant Architecture"

    # Build full remediation SQL script
    remediation_sqls = [f["fixSql"] for f in findings if f.get("fixSql") and not f["fixSql"].startswith("--")]
    remediation_script = "-- ========================================================\n"
    remediation_script += "-- TESTR ERD Studio Pro • Automated Schema Remediation Script\n"
    remediation_script += f"-- Health Score: {health_score}/100 ({grade}) • {len(findings)} Findings\n"
    remediation_script += "-- ========================================================\n\n"
    remediation_script += "\n\n".join(remediation_sqls) if remediation_sqls else "-- لا توجد إصلاحات مطلوبة، المخطط سليم 100%!"

    return {
        "score": health_score,
        "grade": grade,
        "rating_ar": rating_ar,
        "rating_en": rating_en,
        "counts": {
            "critical": critical_count,
            "warning": warning_count,
            "info": info_count,
            "total": len(findings)
        },
        "findings": findings,
        "remediationScript": remediation_script
    }
