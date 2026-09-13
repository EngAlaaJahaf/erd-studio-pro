"""Schema Diff & Migration Generator Service.
Compares two database schemas (Source vs Target) and generates:
1. Structured visual diff (Added/Dropped/Modified tables, columns, PKs, FKs).
2. Forward migration script (ALTER TABLE DDL) for Oracle, PostgreSQL, MySQL, SQLite, and SQL Server.
3. Rollback (Down) migration script.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime


def compare_schemas(
    source_schema: Dict[str, Any],
    target_schema: Dict[str, Any],
    dialect: str = "oracle"
) -> Dict[str, Any]:
    """Compare source schema (baseline) with target schema (new state)."""
    src_tables = source_schema.get("tablesData") or {}
    tgt_tables = target_schema.get("tablesData") or {}
    src_fks = source_schema.get("fkList") or []
    tgt_fks = target_schema.get("fkList") or []

    src_names = set(src_tables.keys())
    tgt_names = set(tgt_tables.keys())

    added_table_names = sorted(list(tgt_names - src_names))
    dropped_table_names = sorted(list(src_names - tgt_names))
    common_table_names = sorted(list(src_names & tgt_names))

    modified_tables: Dict[str, Any] = {}

    for tname in common_table_names:
        st = src_tables[tname]
        tt = tgt_tables[tname]

        s_cols_map = {c["name"].upper(): c for c in st.get("columns", [])}
        t_cols_map = {c["name"].upper(): c for c in tt.get("columns", [])}

        s_col_names = set(s_cols_map.keys())
        t_col_names = set(t_cols_map.keys())

        added_cols = [t_cols_map[c] for c in sorted(list(t_col_names - s_col_names))]
        dropped_cols = [s_cols_map[c] for c in sorted(list(s_col_names - t_col_names))]
        altered_cols = []

        for cname in sorted(list(s_col_names & t_col_names)):
            sc = s_cols_map[cname]
            tc = t_cols_map[cname]
            changes = []
            if (sc.get("type") or "").strip().lower() != (tc.get("type") or "").strip().lower():
                changes.append({
                    "property": "type",
                    "old": sc.get("type"),
                    "new": tc.get("type")
                })
            if bool(sc.get("nullable", True)) != bool(tc.get("nullable", True)):
                changes.append({
                    "property": "nullable",
                    "old": sc.get("nullable", True),
                    "new": tc.get("nullable", True)
                })
            if sc.get("default") != tc.get("default"):
                changes.append({
                    "property": "default",
                    "old": sc.get("default"),
                    "new": tc.get("default")
                })
            if changes:
                altered_cols.append({
                    "name": tc["name"],
                    "oldColumn": sc,
                    "newColumn": tc,
                    "changes": changes
                })

        # Check PK changes
        s_pks = [p.upper() for p in (st.get("pks") or [])]
        t_pks = [p.upper() for p in (tt.get("pks") or [])]
        pk_changed = (set(s_pks) != set(t_pks))

        if added_cols or dropped_cols or altered_cols or pk_changed:
            modified_tables[tname] = {
                "addedColumns": added_cols,
                "droppedColumns": dropped_cols,
                "alteredColumns": altered_cols,
                "pkChanged": pk_changed,
                "oldPks": st.get("pks") or [],
                "newPks": tt.get("pks") or []
            }

    # Compare FKs
    def _fk_key(fk):
        c = (fk.get("child") or "").upper()
        p = (fk.get("parent") or "").upper()
        col = (fk.get("cols") or fk.get("childCol") or "").upper()
        return f"{c}->{p}:{col}"

    src_fk_map = {_fk_key(f): f for f in src_fks}
    tgt_fk_map = {_fk_key(f): f for f in tgt_fks}

    added_fks = [tgt_fk_map[k] for k in tgt_fk_map if k not in src_fk_map]
    dropped_fks = [src_fk_map[k] for k in src_fk_map if k not in tgt_fk_map]

    # Generate Migration DDL
    forward_ddl = _generate_migration_ddl(
        added_table_names, dropped_table_names, modified_tables,
        added_fks, dropped_fks, tgt_tables, src_tables, dialect=dialect, is_rollback=False
    )
    rollback_ddl = _generate_migration_ddl(
        dropped_table_names, added_table_names,
        _invert_modified_tables(modified_tables),
        dropped_fks, added_fks, src_tables, tgt_tables, dialect=dialect, is_rollback=True
    )

    total_changes = (
        len(added_table_names) + len(dropped_table_names) + len(modified_tables) +
        len(added_fks) + len(dropped_fks)
    )

    return {
        "hasChanges": (total_changes > 0),
        "summary": {
            "addedTablesCount": len(added_table_names),
            "droppedTablesCount": len(dropped_table_names),
            "modifiedTablesCount": len(modified_tables),
            "addedFksCount": len(added_fks),
            "droppedFksCount": len(dropped_fks),
            "totalChanges": total_changes
        },
        "diff": {
            "addedTables": added_table_names,
            "droppedTables": dropped_table_names,
            "modifiedTables": modified_tables,
            "addedFks": added_fks,
            "droppedFks": dropped_fks
        },
        "migrationScript": forward_ddl,
        "rollbackScript": rollback_ddl,
        "dialect": dialect
    }


def _invert_modified_tables(mod_tables: Dict[str, Any]) -> Dict[str, Any]:
    """Invert modified tables for rollback DDL."""
    inv = {}
    for tname, m in mod_tables.items():
        inv_altered = []
        for alt in m.get("alteredColumns", []):
            inv_changes = []
            for ch in alt.get("changes", []):
                inv_changes.append({
                    "property": ch["property"],
                    "old": ch["new"],
                    "new": ch["old"]
                })
            inv_altered.append({
                "name": alt["name"],
                "oldColumn": alt["newColumn"],
                "newColumn": alt["oldColumn"],
                "changes": inv_changes
            })
        inv[tname] = {
            "addedColumns": m.get("droppedColumns", []),
            "droppedColumns": m.get("addedColumns", []),
            "alteredColumns": inv_altered,
            "pkChanged": m.get("pkChanged", False),
            "oldPks": m.get("newPks", []),
            "newPks": m.get("oldPks", [])
        }
    return inv


def _generate_migration_ddl(
    added_tables: List[str],
    dropped_tables: List[str],
    modified_tables: Dict[str, Any],
    added_fks: List[Dict[str, Any]],
    dropped_fks: List[Dict[str, Any]],
    current_tables: Dict[str, Any],
    reference_tables: Dict[str, Any],
    dialect: str = "oracle",
    is_rollback: bool = False
) -> str:
    """Generate dialect-compliant incremental DDL."""
    dia = dialect.lower()
    q = '"' if dia in ("oracle", "postgres") else ("`" if dia == "mysql" else '"')
    lines = []

    header = "-- ========================================================\n"
    header += f"-- TESTR ERD Studio Pro • {'Rollback (Down)' if is_rollback else 'Forward (Up)'} Migration\n"
    header += f"-- Dialect: {dialect.upper()} • Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    header += "-- ========================================================\n"
    lines.append(header)

    # 1. Drop old FKs first to avoid locking or constraint errors
    if dropped_fks:
        lines.append("-- 1. Drop Foreign Keys")
        for fk in dropped_fks:
            c = fk.get("child")
            fk_name = fk.get("name") or f"FK_{c}_{fk.get('parent')}"
            if dia in ("oracle", "postgres", "mssql"):
                lines.append(f'ALTER TABLE {q}{c}{q} DROP CONSTRAINT {q}{fk_name}{q};')
            elif dia == "mysql":
                lines.append(f'ALTER TABLE {q}{c}{q} DROP FOREIGN KEY {q}{fk_name}{q};')
        lines.append("")

    # 2. Drop removed tables
    if dropped_tables:
        lines.append("-- 2. Drop Tables")
        for t in dropped_tables:
            if dia == "oracle":
                lines.append(f'DROP TABLE {q}{t}{q} CASCADE CONSTRAINTS PURGE;')
            elif dia == "postgres":
                lines.append(f'DROP TABLE IF EXISTS {q}{t}{q} CASCADE;')
            else:
                lines.append(f'DROP TABLE IF EXISTS {q}{t}{q};')
        lines.append("")

    # 3. Create newly added tables
    if added_tables:
        lines.append("-- 3. Create New Tables")
        for t in added_tables:
            tdata = current_tables.get(t, {})
            cols = tdata.get("columns", [])
            pks = tdata.get("pks") or []
            col_defs = []
            for c in cols:
                cname = c["name"]
                ctype = c.get("type") or "VARCHAR2(100)"
                null_str = " NOT NULL" if (c.get("nullable") is False or cname in pks) else ""
                col_defs.append(f'  {q}{cname}{q} {ctype}{null_str}')
            if pks:
                pk_cols_str = ", ".join(f'{q}{p}{q}' for p in pks)
                col_defs.append(f'  CONSTRAINT {q}PK_{t}{q} PRIMARY KEY ({pk_cols_str})')

            body = ",\n".join(col_defs)
            lines.append(f'CREATE TABLE {q}{t}{q} (\n{body}\n);')
        lines.append("")

    # 4. Alter existing tables (Add, Drop, Modify columns, Changed PKs)
    if modified_tables:
        lines.append("-- 4. Alter Existing Tables")
        for tname, m in modified_tables.items():
            # Dropped columns
            for col in m.get("droppedColumns", []):
                cname = col["name"]
                if dia == "oracle":
                    lines.append(f'ALTER TABLE {q}{tname}{q} DROP COLUMN {q}{cname}{q};')
                elif dia in ("postgres", "mysql"):
                    lines.append(f'ALTER TABLE {q}{tname}{q} DROP COLUMN {q}{cname}{q};')

            # Added columns
            for col in m.get("addedColumns", []):
                cname = col["name"]
                ctype = col.get("type") or "VARCHAR2(100)"
                null_str = " NOT NULL" if col.get("nullable") is False else ""
                if dia in ("oracle", "postgres", "mysql"):
                    lines.append(f'ALTER TABLE {q}{tname}{q} ADD {q}{cname}{q} {ctype}{null_str};')

            # Altered columns
            for alt in m.get("alteredColumns", []):
                cname = alt["name"]
                new_col = alt["newColumn"]
                new_type = new_col.get("type") or "VARCHAR2(100)"
                null_str = " NOT NULL" if new_col.get("nullable") is False else " NULL"
                if dia == "oracle":
                    lines.append(f'ALTER TABLE {q}{tname}{q} MODIFY ({q}{cname}{q} {new_type}{null_str});')
                elif dia == "postgres":
                    lines.append(f'ALTER TABLE {q}{tname}{q} ALTER COLUMN {q}{cname}{q} TYPE {new_type};')
                    if new_col.get("nullable") is False:
                        lines.append(f'ALTER TABLE {q}{tname}{q} ALTER COLUMN {q}{cname}{q} SET NOT NULL;')
                    else:
                        lines.append(f'ALTER TABLE {q}{tname}{q} ALTER COLUMN {q}{cname}{q} DROP NOT NULL;')
                elif dia == "mysql":
                    lines.append(f'ALTER TABLE {q}{tname}{q} MODIFY COLUMN {q}{cname}{q} {new_type}{null_str};')

            # Changed PKs
            if m.get("pkChanged"):
                new_pks = m.get("newPks") or []
                if dia == "oracle":
                    lines.append(f'-- Rebuild Primary Key on {tname}')
                    lines.append(f'ALTER TABLE {q}{tname}{q} DROP PRIMARY KEY;')
                    if new_pks:
                        pk_str = ", ".join(f'{q}{p}{q}' for p in new_pks)
                        lines.append(f'ALTER TABLE {q}{tname}{q} ADD CONSTRAINT {q}PK_{tname}{q} PRIMARY KEY ({pk_str});')
                elif dia == "postgres":
                    lines.append(f'ALTER TABLE {q}{tname}{q} DROP CONSTRAINT IF EXISTS {q}{tname}_pkey{q};')
                    if new_pks:
                        pk_str = ", ".join(f'{q}{p}{q}' for p in new_pks)
                        lines.append(f'ALTER TABLE {q}{tname}{q} ADD PRIMARY KEY ({pk_str});')
                elif dia == "mysql":
                    lines.append(f'ALTER TABLE {q}{tname}{q} DROP PRIMARY KEY;')
                    if new_pks:
                        pk_str = ", ".join(f'{q}{p}{q}' for p in new_pks)
                        lines.append(f'ALTER TABLE {q}{tname}{q} ADD PRIMARY KEY ({pk_str});')
        lines.append("")

    # 5. Add new Foreign Keys
    if added_fks:
        lines.append("-- 5. Add New Foreign Key Constraints")
        for fk in added_fks:
            c = fk.get("child")
            p = fk.get("parent")
            col = fk.get("cols") or fk.get("childCol")
            p_col = fk.get("parentCol")
            if not p_col:
                p_pks = current_tables.get(p, {}).get("pks") or []
                p_col = p_pks[0] if p_pks else "ID"
            fk_name = fk.get("name") or f"FK_{c}_{p}"
            lines.append(
                f'ALTER TABLE {q}{c}{q} ADD CONSTRAINT {q}{fk_name}{q} '
                f'FOREIGN KEY ({q}{col}{q}) REFERENCES {q}{p}{q} ({q}{p_col}{q});'
            )
        lines.append("")

    if len(lines) <= 2:
        return header + "\n-- لا توجد فروقات بين المخططين (المخططان متطابقان تماماً)."

    return "\n".join(lines)
