"""Smart Mock Data Generator Service.
Generates realistic, constraint-compliant INSERT statements with:
1. Topological sorting (DAG) to ensure parent tables are populated before child tables.
2. Semantic-aware value generation based on column names (names, emails, phones, IDs, amounts, dates, statuses).
3. Strict Foreign Key integrity (draws FK values from actually generated parent PKs).
"""

import random
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

AR_NAMES = [
    "محمد العتيبي", "عبدالله الشمري", "سارة القحطاني", "فهد الدوسري", "نورة الغامدي",
    "خالد الزهراني", "ريم الحربي", "عمر السعيد", "منى الشهري", "أحمد المطيري",
    "فيصل العنزي", "هند المالكي", "سلطان البقمي", "روان السبيعي", "ياسر التميمي"
]

EN_NAMES = [
    "John Smith", "Emma Johnson", "Michael Brown", "Olivia Davis", "James Wilson",
    "Sophia Martinez", "David Anderson", "Emily Taylor", "Daniel Thomas", "Sarah White"
]

AR_CITIES = ["الرياض", "جدة", "الدمام", "مكة المكرمة", "المدينة المنورة", "الخبر", "أبها", "تبوك"]
EN_CITIES = ["Riyadh", "Jeddah", "Dammam", "Dubai", "Cairo", "Doha", "Manama", "London"]

STATUSES = ["ACTIVE", "INACTIVE", "PENDING", "APPROVED", "COMPLETED", "SUSPENDED"]
CURRENCIES = ["SAR", "USD", "EUR", "AED", "KWD"]


def _topological_sort(tables_data: Dict[str, Any], fk_list: List[Dict[str, Any]]) -> List[str]:
    """Sort tables so that referenced parent tables appear before dependent child tables."""
    adj: Dict[str, set] = {t: set() for t in tables_data}
    in_degree: Dict[str, int] = {t: 0 for t in tables_data}

    for fk in fk_list:
        child = fk.get("child")
        parent = fk.get("parent")
        if child in tables_data and parent in tables_data and child != parent:
            if child not in adj[parent]:
                adj[parent].add(child)
                in_degree[child] += 1

    # Kahn's algorithm
    queue = [t for t in tables_data if in_degree[t] == 0]
    sorted_tables = []

    while queue:
        u = queue.pop(0)
        sorted_tables.append(u)
        for v in adj[u]:
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)

    # In case of cycles, append remaining tables
    for t in tables_data:
        if t not in sorted_tables:
            sorted_tables.append(t)

    return sorted_tables


def _generate_semantic_value(
    col_name: str,
    col_type: str,
    row_idx: int,
    is_pk: bool,
    lang: str = "ar"
) -> Any:
    """Generate realistic value based on column name heuristics and data type."""
    cn = col_name.lower()
    ct = (col_type or "").lower()

    # 1. Primary Key / Serial ID
    if is_pk:
        if any(num in ct for num in ("int", "number", "serial", "numeric")):
            return 1000 + row_idx
        else:
            return f"PK_{1000 + row_idx}"

    # 2. Email
    if "email" in cn or "mail" in cn:
        return f"user_{row_idx + 1}@example.com"

    # 3. Phone / Mobile
    if any(p in cn for p in ("phone", "mobile", "tel", "cell")):
        return f"+9665{random.randint(10000000, 99999999)}"

    # 4. National ID / Iqama / SSN
    if any(nid in cn for nid in ("national_id", "iqama", "ssn", "civil_id", "identity")):
        prefix = "1" if row_idx % 2 == 0 else "2"
        return f"{prefix}{random.randint(100000000, 999999999)}"

    # 5. Person Name
    if any(n in cn for n in ("name", "full_name", "first_name", "emp_name", "cust_name", "student_name", "user_name")):
        if "user_name" in cn or "username" in cn:
            return f"usr_{row_idx + 1}"
        names = AR_NAMES if lang == "ar" else EN_NAMES
        return names[row_idx % len(names)]

    # 6. Currency
    if "curr" in cn:
        return CURRENCIES[row_idx % len(CURRENCIES)]

    # 7. Status
    if "status" in cn or "state" in cn:
        return STATUSES[row_idx % len(STATUSES)]

    # 8. City / Country / Address
    if "city" in cn:
        cities = AR_CITIES if lang == "ar" else EN_CITIES
        return cities[row_idx % len(cities)]
    if "country" in cn:
        return "المملكة العربية السعودية" if lang == "ar" else "Saudi Arabia"
    if "address" in cn or "street" in cn:
        return f"شارع الملك فهد، مبنى {10 + row_idx}" if lang == "ar" else f"King Fahd Rd, Bldg {10 + row_idx}"

    # 9. Amount / Salary / Price / Total / Balance
    if any(m in cn for m in ("amount", "salary", "price", "total", "balance", "cost", "fee", "rate")):
        if "rate" in cn or "pct" in cn or "percent" in cn:
            return round(random.uniform(5.0, 25.0), 2)
        return round(random.uniform(250.0, 15000.0), 2)

    # 10. Date / Timestamp
    if any(d in cn for d in ("date", "time", "created_at", "updated_at", "birth")):
        base_date = datetime.now() - timedelta(days=random.randint(1, 365))
        if "birth" in cn:
            base_date = datetime(1992, 1, 1) + timedelta(days=random.randint(0, 5000))
        return base_date.strftime("%Y-%m-%d")

    # 11. Generic Numeric
    if any(num in ct for num in ("number", "int", "numeric", "float", "decimal")):
        return (row_idx + 1) * 10

    # 12. Generic Text fallback
    return f"Test_{cn[:8]}_{row_idx + 1}"


def generate_mock_data(
    tables_data: Dict[str, Any],
    fk_list: List[Dict[str, Any]],
    row_count: int = 10,
    dialect: str = "oracle",
    lang: str = "ar"
) -> Dict[str, Any]:
    """Generate realistic, constraint-compliant INSERT SQL statements."""
    dia = dialect.lower()
    q = '"' if dia in ("oracle", "postgres") else ("`" if dia == "mysql" else '"')
    
    sorted_tables = _topological_sort(tables_data, fk_list)
    generated_pks: Dict[str, Dict[str, List[Any]]] = {}

    # Map FK columns: child_table -> child_col -> (parent_table, parent_col)
    fk_lookup: Dict[str, Dict[str, tuple]] = {}
    for fk in fk_list:
        c = fk.get("child")
        p = fk.get("parent")
        cc = (fk.get("cols") or fk.get("childCol") or "").upper()
        pc = (fk.get("parentCol") or "").upper()
        if not pc and p in tables_data:
            p_pks = tables_data[p].get("pks") or []
            pc = p_pks[0].upper() if p_pks else "ID"
        if c not in fk_lookup:
            fk_lookup[c] = {}
        fk_lookup[c][cc] = (p, pc)

    table_sql_blocks: List[str] = []
    total_rows = 0

    header = "-- ========================================================\n"
    header += f"-- TESTR ERD Studio Pro • Smart Mock Data Generator\n"
    header += f"-- Target Dialect: {dialect.upper()} • Rows Per Table: {row_count} • Locale: {lang.upper()}\n"
    header += f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    header += "-- ========================================================\n\n"

    if dia == "oracle":
        header += "SET DEFINE OFF;\nALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD';\n\n"

    for tname in sorted_tables:
        tdata = tables_data.get(tname)
        if not tdata:
            continue
        cols = tdata.get("columns", [])
        pks = set(p.upper() for p in (tdata.get("pks") or []))
        if not cols:
            continue

        generated_pks[tname] = {pk: [] for pk in pks}
        col_names = [c["name"] for c in cols]
        quoted_col_names = ", ".join(f"{q}{c}{q}" for c in col_names)

        t_insert_lines = [f"-- Table: {tname} ({row_count} rows)"]

        for r_idx in range(row_count):
            row_vals = []
            for col in cols:
                cname = col["name"]
                ctype = col.get("type", "")
                is_pk = (cname.upper() in pks)
                val = None

                # Check if this column is a Foreign Key
                if tname in fk_lookup and cname.upper() in fk_lookup[tname]:
                    parent_tbl, parent_col = fk_lookup[tname][cname.upper()]
                    parent_vals = generated_pks.get(parent_tbl, {}).get(parent_col, [])
                    if parent_vals:
                        val = random.choice(parent_vals)

                # If not FK or parent had no values, generate semantic value
                if val is None:
                    val = _generate_semantic_value(cname, ctype, r_idx, is_pk, lang=lang)

                # Store PK value for children to reference
                if is_pk and cname.upper() in generated_pks[tname]:
                    generated_pks[tname][cname.upper()].append(val)

                # Format SQL literal
                if isinstance(val, (int, float)):
                    row_vals.append(str(val))
                elif isinstance(val, str):
                    # Check if date
                    if re.match(r"^\d{4}-\d{2}-\d{2}$", val):
                        if dia == "oracle":
                            row_vals.append(f"TO_DATE('{val}', 'YYYY-MM-DD')")
                        else:
                            row_vals.append(f"'{val}'")
                    else:
                        escaped = val.replace("'", "''")
                        row_vals.append(f"'{escaped}'")
                elif val is None:
                    row_vals.append("NULL")
                else:
                    row_vals.append(f"'{val}'")

            values_str = ", ".join(row_vals)
            t_insert_lines.append(f"INSERT INTO {q}{tname}{q} ({quoted_col_names}) VALUES ({values_str});")
            total_rows += 1

        table_sql_blocks.append("\n".join(t_insert_lines))

    footer = "\nCOMMIT;\n-- Data insertion completed successfully!"
    full_script = header + "\n\n".join(table_sql_blocks) + footer

    return {
        "success": True,
        "tableCount": len(sorted_tables),
        "totalRows": total_rows,
        "topologicalOrder": sorted_tables,
        "script": full_script,
        "dialect": dialect
    }
