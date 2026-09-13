"""Generate SQL DDL (CREATE TABLE + FOREIGN KEY constraints) from the unified
tablesData / fkList model, targeting any supported dialect.

Dialects: oracle, mysql, postgres, sqlite, mssql, ansi
"""

import re

DIALECTS = ["oracle", "mysql", "postgres", "sqlite", "mssql", "ansi"]

_DROP_SQL = {
    "oracle": 'DROP TABLE "{t}" CASCADE CONSTRAINTS;',
    "mysql": "DROP TABLE IF EXISTS `{t}`;",
    "postgres": 'DROP TABLE IF EXISTS "{t}" CASCADE;',
    "sqlite": 'DROP TABLE IF EXISTS "{t}";',
    "mssql": 'DROP TABLE IF EXISTS [dbo].[{t}];',
    "ansi": 'DROP TABLE IF EXISTS "{t}";',
}

_QOPEN = {"oracle": '"', "mysql": "`", "postgres": '"', "sqlite": '"', "mssql": "[", "ansi": '"'}
_QCLOSE = {"oracle": '"', "mysql": "`", "postgres": '"', "sqlite": '"', "mssql": "]", "ansi": '"'}


def _ident(dialect, name):
    name = str(name)
    return f"{_QOPEN[dialect]}{name}{_QCLOSE[dialect]}"


def _table_ident(dialect, name):
    name = str(name)
    if dialect == "mssql":
        return f"[dbo].[{name}]"
    return _ident(dialect, name)


def _split_type(display):
    m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(\(.*\))?\s*$", str(display).strip())
    if not m:
        return str(display).strip(), ""
    return m.group(1).lower(), (m.group(2) or "").strip()


def convert_type(display, dialect):
    base, params = _split_type(display)

    def keep(rep=None):
        return f"{rep or base}{params}"

    if base in ("varchar", "varchar2", "nvarchar2", "nvarchar", "char", "nchar", "character", "text", "clob"):
        if dialect == "oracle":
            if base == "text":
                return "CLOB"
            if base in ("nvarchar2", "nchar"):
                return f"{base.upper()}{params}"
            if base == "char":
                return f"CHAR{params or '(1)'}"
            return f"VARCHAR2{params}"
        if dialect == "mssql":
            if base == "text":
                return "NVARCHAR(MAX)"
            if base in ("char", "nchar"):
                return f"{base.upper()}{params or '(1)'}"
            return f"NVARCHAR{params or '(MAX)'}"
        if dialect == "sqlite":
            return "TEXT"
        if base == "text":
            return params.upper() if dialect != "postgres" else "TEXT"
        if base in ("varchar2", "nvarchar2", "nvarchar"):
            return f"VARCHAR{params}"
        return f"{base.upper() if base != 'character' else 'CHAR'}{params}"

    if base in ("int", "integer", "smallint", "bigint", "mediumint", "tinyint", "number", "decimal", "numeric", "float", "double", "real"):
        if dialect == "oracle":
            if base == "int":
                return "INTEGER"
            if base == "smallint":
                return "SMALLINT"
            if base == "bigint":
                return "NUMBER(19)"
            if base == "float":
                return "FLOAT"
            if base in ("number", "decimal", "numeric"):
                return f"NUMBER{params if params else ''}"
            return f"NUMBER{params}"
        if base == "number":
            return f"DECIMAL{params if params else ''}" if dialect != "mysql" else f"DECIMAL{params or '(10,2)'}"
        if base in ("decimal", "numeric"):
            return f"{base.upper()}{params}"
        if base in ("int", "integer", "smallint", "bigint", "mediumint", "tinyint"):
            return base.upper() if dialect != "mysql" else base
        if base == "double":
            return "DOUBLE PRECISION" if dialect in ("postgres", "ansi") else "DOUBLE"
        return base.upper()

    if base in ("boolean", "bool"):
        if dialect == "mysql":
            return "TINYINT(1)"
        if dialect == "oracle":
            return "NUMBER(1)"
        if dialect == "mssql":
            return "BIT"
        return "BOOLEAN"

    if base in ("timestamp", "datetime", "date", "time", "timestamptz"):
        if dialect == "mssql" and base == "timestamp":
            return "DATETIME2"
        return base.upper() if base in ("date", "time") else ("TIMESTAMP WITH TIME ZONE" if base == "timestamptz" and dialect != "mysql" else ("TIMESTAMP" if base == "timestamp" else "DATETIME" if base == "datetime" and dialect == "mysql" else base.upper()))

    if base == "blob":
        if dialect == "mysql":
            return "LONGBLOB"
        if dialect == "mssql":
            return "VARBINARY(MAX)"
        if dialect == "postgres":
            return "BYTEA"
        return "BLOB"

    if base == "json":
        if dialect == "postgres":
            return "JSONB"
        if dialect == "oracle":
            return "CLOB"
        if dialect == "mssql":
            return "NVARCHAR(MAX)"
        return "JSON"

    if base == "uuid":
        if dialect == "postgres":
            return "UUID"
        return "VARCHAR(36)"

    return keep()


def generate_ddl(tables_data, fk_list, dialect="mysql", include_drop=True, separately=False):
    """Generate DDL text for a schema model.

    separately=True: return a dict {table_name: ddl} (useful for per-table scripts).
    """
    if dialect not in DIALECTS:
        dialect = "ansi"
    tables = list(tables_data.keys())
    out_lines = []

    fk_by_child = {}
    for f in fk_list:
        fk_by_child.setdefault(f["child"], []).append(f)

    parts = {}
    for t in sorted(tables):
        data = tables_data[t]
        lines = []
        if include_drop:
            lines.append(_DROP_SQL[dialect].format(t=t))
            lines.append("")
        lines.append(f"CREATE TABLE {_table_ident(dialect, t)} (")
        body_lines = []
        pks = data.get("pks") or []
        for col in data.get("columns", []):
            name = col["name"]
            txt = f"  {_ident(dialect, name)} {convert_type(col.get('type', 'TEXT'), dialect)}"
            if col.get("nullable") is False:
                txt += " NOT NULL"
            if dialect == "mysql" and len(pks) == 1 and pks[0] == name:
                txt += " AUTO_INCREMENT"
            body_lines.append(txt)
        if pks:
            body_lines.append(f"  PRIMARY KEY ({', '.join(_ident(dialect, p) for p in pks)})")
        for f in fk_by_child.get(t, []):
            fk_name = f.get("fk") or f"FK_{f['child']}_{f['parent']}"
            child_cols = [c.strip() for c in (f.get("cols") or "").split(",") if c.strip()]
            parent_cols = [c.strip() for c in (f.get("pcols") or "").split(",") if c.strip()]
            if not parent_cols:
                parent_cols = child_cols
            body_lines.append(
                f"  CONSTRAINT {_ident(dialect, fk_name)} FOREIGN KEY "
                f"({', '.join(_ident(dialect, c) for c in child_cols)}) "
                f"REFERENCES {_table_ident(dialect, f['parent'])} "
                f"({', '.join(_ident(dialect, c) for c in parent_cols)})"
            )
        lines.append(",\n".join(body_lines))
        table_comment = data.get("comment") or data.get("description")
        if dialect == "mysql" and table_comment:
            escaped_t = str(table_comment).replace("'", "''")
            lines.append(f") COMMENT = '{escaped_t}';")
        else:
            lines.append(");")

        # Column & Table Comments (Oracle, PostgreSQL, ANSI)
        if dialect in ("oracle", "postgres", "ansi"):
            if table_comment:
                escaped_t = str(table_comment).replace("'", "''")
                lines.append(f"COMMENT ON TABLE {_table_ident(dialect, t)} IS '{escaped_t}';")
            for col in data.get("columns", []):
                col_cmt = col.get("comment") or col.get("description")
                if col_cmt and col_cmt != "-":
                    escaped_c = str(col_cmt).replace("'", "''")
                    lines.append(f"COMMENT ON COLUMN {_table_ident(dialect, t)}.{_ident(dialect, col['name'])} IS '{escaped_c}';")

        parts[t] = "\n".join(lines)

    if separately:
        return parts
    return "\n\n".join(parts.values()) + "\n"


def generate_export_payload(tables_data, fk_list, dialect="mysql", include_drop=True):
    """Endpoint-friendly payload: full script + preview stats."""
    if not tables_data:
        return {"success": False, "error": "No schema loaded"}
    try:
        ddl = generate_ddl(tables_data, fk_list, dialect, include_drop)
    except Exception as e:
        return {"success": False, "error": str(e)}
    return {
        "success": True,
        "dialect": dialect,
        "script": ddl,
        "tableCount": len(tables_data),
        "fkCount": len(fk_list),
        "sizeBytes": len(ddl.encode("utf-8")),
    }