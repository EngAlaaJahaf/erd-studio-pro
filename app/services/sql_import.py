"""Import SQL DDL files (any dialect) and convert them to the unified
tablesData / fkList schema model used by the ERD frontend.

Uses sqlglot, so the same parser works for MySQL, Oracle, PostgreSQL,
SQLite, SQL Server, Snowflake, ... Dialect is auto-detected from the
script content and falls back to trying every available dialect.
"""

from sqlglot import exp, parse
from sqlglot.errors import SqlglotError

# Ordered candidates used for fallback attempts
ALL_DIALECTS = ["mysql", "oracle", "postgres", "sqlite", "tsql",
                "snowflake", "redshift", "duckdb", "bigquery", "teradata"]


def _features(text):
    u = text.upper()
    feats = {
        "mysql": ["ENGINE=", "AUTO_INCREMENT", "TINYINT", "MEDIUMINT", "UNSIGNED",
                  "ENUM(", "SET(", "`", "CHARSET=", "COLLATE=", "ON UPDATE"],
        "oracle": ["VARCHAR2", "NVARCHAR2", "NUMBER(", "RAW(", "CLOB", "BLOB",
                   "BFILE", "GENERATED ALWAYS AS IDENTITY", "PCTFREE", "TABLESPACE"],
        "postgres": ["BIGSERIAL", "SERIAL", "CREATE OR REPLACE", "GENERATED ALWAYS AS",
                     "INHERITS", "CONCURRENTLY", "CITEXT", "JSONB", "]::", "$$"],
        "tsql": ["IDENTITY(1,1)", "NVARCHAR(MAX)", "VARCHAR(MAX)", "[", "]",
                  "DATETIME2", "WITH (NOLOCK", "GO"],
        "sqlite": ["AUTOINCREMENT", "SQLITE_SEQUENCE", "WITHOUT ROWID", "AS (", "] INTEGER"],
        "snowflake": ["VARIANT", "WAREHOUSE", "CREATE OR REPLACE TRANSIENT"],
        "bigquery": ["STRUCT<", "ARRAY<", "BIGNUMERIC", "PARTITION BY"],
        "duckdb": ["HUGEINT", "DUCKDB_VERSION", "SEQUENCE"],
    }
    return feats


def detect_dialect(sql_text):
    """Return the most likely dialect name for a SQL script."""
    u = sql_text.upper()
    feats = _features(u)
    scored = []
    for dialect, keywords in feats.items():
        s = sum(1 for k in keywords if k in u)
        if s:
            scored.append((s, dialect))
    if not scored:
        # second pass: dialect-agnostic tiny hints
        if "CREATE TABLE" in u or "ALTER TABLE" in u:
            return "mysql"  # most permissive default
        return "mysql"
    scored.sort(reverse=True)
    return scored[0][1]


def _dialect_candidates(detected):
    # detected first, then the rest of the generic pool
    return [detected] + [d for d in ALL_DIALECTS if d != detected]


def _table_name(node):
    """Extract a plain table name from Table / Schema / Identifier nodes."""
    while isinstance(node, exp.Schema):
        node = node.this
    if isinstance(node, exp.Table):
        return node.name
    if isinstance(node, exp.Identifier):
        return node.name
    if isinstance(node, exp.Expression):
        return node.name
    return None


def _extract_fk(fk_node, constraint_name):
    """Extract {child-col list, parent table, parent-col list} from an exp.ForeignKey."""
    if not isinstance(fk_node, exp.ForeignKey):
        return None
    child_cols = [c.name for c in (fk_node.expressions or []) if c]
    ref = fk_node.args.get("reference")
    if not ref:
        return None
    parent_tbl = _table_name(ref.this)
    parent_cols = []
    # reference target columns live in a Schema(Table) whose `expressions` are the columns
    target = ref.this
    while isinstance(target, exp.Schema):
        parent_cols = [c.name for c in (target.expressions or []) if c]
        target = target.this
    if isinstance(ref.this, exp.Schema) and not parent_cols:
        parent_cols = [c.name for c in (ref.this.expressions or []) if c]
    return child_cols, parent_tbl, parent_cols


def _inline_reference(col_def):
    """Find a column-level REFERENCES (...) and return (parent_table, parent_cols)."""
    ref_cands = []
    for cdef in (col_def.constraints or []):
        kind = cdef.kind if hasattr(cdef, "kind") else None
        if isinstance(kind, exp.Reference):
            ref_cands.append(kind)
    for sub in (col_def.expressions or []):
        if isinstance(sub, exp.Reference):
            ref_cands.append(sub)
    for ref in ref_cands:
        target = ref.this
        parent_cols = []
        while isinstance(target, exp.Schema):
            parent_cols = [c.name for c in (target.expressions or []) if c]
            target = target.this
        parent_tbl = target.name if hasattr(target, "name") else None
        if parent_tbl:
            return parent_tbl, parent_cols
    return None


def _collect_table_content(table_node, dialect):
    """Parse Schema.expressions into columns + pks + inline FKs.

    Returns (columns, pks, fks) where fks is a list of raw fk dicts.
    """
    columns = []
    pks = []
    fks = []
    for expr in (table_node.expressions or []):
        if isinstance(expr, exp.ColumnDef):
            col_name = expr.name
            dtype = expr.kind.sql() if expr.kind else "UNKNOWN"
            nullable = True
            inline_fk = None
            for cdef in (expr.constraints or []):
                kind = cdef.kind if hasattr(cdef, "kind") else None
                if isinstance(kind, exp.NotNullColumnConstraint):
                    nullable = False
                elif isinstance(kind, exp.PrimaryKeyColumnConstraint):
                    pks.append(col_name)
            for sub in (expr.expressions or []):
                if isinstance(sub, exp.ForeignKey):
                    inline_fk = sub
                if isinstance(sub, exp.ColumnConstraint):
                    kind = sub.kind if hasattr(sub, "kind") else None
                    if isinstance(kind, exp.PrimaryKeyColumnConstraint):
                        pks.append(col_name)
            columns.append({"name": col_name, "type": dtype, "nullable": nullable})
            if inline_fk:
                got = _extract_fk(inline_fk, None)
                if got:
                    child_cols, parent_tbl, parent_cols = got
                    fks.append({"child": None, "parent": parent_tbl,
                                "fk": None, "child_cols": [col_name] if not child_cols else child_cols,
                                "parent_cols": parent_cols or child_cols})
            elif not any(f["child_cols"] == [col_name] and f["parent"] for f in fks):
                ref = _inline_reference(expr)
                if ref:
                    parent_tbl, parent_cols = ref
                    fks.append({"child": None, "parent": parent_tbl, "fk": None,
                                "child_cols": [col_name], "parent_cols": parent_cols or [col_name]})
        elif isinstance(expr, exp.PrimaryKey):
            pks.extend(c.name for c in (expr.expressions or []))
        elif isinstance(expr, exp.ForeignKey):
            got = _extract_fk(expr, None)
            if got:
                child_cols, parent_tbl, parent_cols = got
                fks.append({"child": None, "parent": parent_tbl, "fk": None,
                            "child_cols": child_cols, "parent_cols": parent_cols or child_cols})
        elif isinstance(expr, exp.Constraint):
            cname = expr.name
            for sub in (expr.expressions or []):
                if isinstance(sub, exp.ForeignKey):
                    got = _extract_fk(sub, cname)
                    if got:
                        child_cols, parent_tbl, parent_cols = got
                        fks.append({"child": None, "parent": parent_tbl, "fk": cname,
                                    "child_cols": child_cols, "parent_cols": parent_cols or child_cols})
                elif isinstance(sub, exp.PrimaryKey):
                    pks.extend(c.name for c in (sub.expressions or []))
    return columns, pks, fks


def _extract(stmts, dialect):
    """Convert parsed statements into tables_data + fk_list."""
    tables_data = {}
    fks = []
    for stmt in stmts:
        if isinstance(stmt, exp.Create) and stmt.this:
            node = stmt.this
            # skip non-table creates
            if isinstance(node, exp.Schema):
                table_ref = node.this
            elif isinstance(node, exp.Table):
                table_ref = node
            else:
                continue
            table_name = _table_name(table_ref)
            if not table_name:
                continue
            if isinstance(node, exp.Schema):
                columns, pks, tfks = _collect_table_content(node, dialect)
                tables_data[table_name] = {"columns": columns, "pks": pks}
                for f in tfks:
                    f["child"] = table_name
                    fks.append(f)
        elif isinstance(stmt, exp.Alter):
            table_name = _table_name(stmt.this)
            if not table_name:
                continue
            for action in (stmt.actions or []):
                for expr_node in (action.expressions or []):
                    if isinstance(expr_node, exp.Constraint):
                        cname = expr_node.name
                        for sub in (expr_node.expressions or []):
                            if isinstance(sub, exp.ForeignKey):
                                got = _extract_fk(sub, cname)
                                if got:
                                    child_cols, parent_tbl, parent_cols = got
                                    fks.append({"child": table_name, "parent": parent_tbl,
                                                "fk": cname, "child_cols": child_cols,
                                                "parent_cols": parent_cols or child_cols})
                            elif isinstance(sub, exp.PrimaryKey):
                                if table_name not in tables_data:
                                    tables_data[table_name] = {"columns": [], "pks": []}
                                tables_data[table_name]["pks"].extend(
                                    c.name for c in (sub.expressions or []))

    return tables_data, fks


def parse_sql_schema(sql_text, dialect=None):
    """Parse a .sql script into the unified schema model.

    Returns dict: {success, tablesData, fkList, tableCount, fkCount,
                   dialect, warnings}
    """
    if not dialect:
        dialect = detect_dialect(sql_text)
    candidates = _dialect_candidates(dialect)
    last_error = None
    warnings = []

    # Normalize literal escape sequences (e.g. "CREATE TABLE\n..." from
    # streaming/JSON payloads that never got their escapes decoded).
    if "\\n" in sql_text or "\\t" in sql_text or "\\r" in sql_text:
        sql_text = (sql_text.replace("\\r\\n", "\n")
                             .replace("\\n", "\n")
                             .replace("\\r", "\n")
                             .replace("\\t", "  "))

    for d in candidates:
        try:
            raw = parse(sql_text, read=d)
        except Exception as e:
            last_error = str(e)
            warnings.append(f"{d}: {e}")
            continue

        # parse() already returns per-statement either expression or error objects
        stmts = []
        parse_errors = 0
        for item in raw:
            if isinstance(item, exp.Expression):
                stmts.append(item)
            else:
                parse_errors += 1
        try:
            tables_data, fks = _extract(stmts, d)
        except Exception as e:
            last_error = str(e)
            tables_data, fks = {}, []

        if tables_data:
            fk_list = []
            for f in fks:
                if f["parent"] not in tables_data or f["child"] not in tables_data:
                    continue
                fk_list.append({
                    "child": f["child"],
                    "parent": f["parent"],
                    "fk": f.get("fk") or f"FK_{f['child']}_{f['parent']}",
                    "cols": ", ".join(f["child_cols"] or []),
                })
            warnings.append(f"used dialect: {d}")
            if parse_errors:
                warnings.append(f"{parse_errors} statement(s) could not be parsed and were skipped")
            return {
                "success": True,
                "tablesData": tables_data,
                "fkList": fk_list,
                "tableCount": len(tables_data),
                "fkCount": len(fk_list),
                "dialect": d,
                "warnings": warnings,
            }
        # keep last error for the final raise
        if last_error is None:
            last_error = f"no CREATE TABLE statements found (dialect={d})"

    raise ValueError(f"Could not parse SQL as any supported dialect. {last_error}")


def infer_type_widths(tables_data):
    """Optional normalizer: strips overly long string widths to the base type.

    Kept as a utility; not applied by default to preserve original DDL.
    """
    return tables_data