"""Unified database connectors: load a schema (tablesData / fkList) from
MySQL, PostgreSQL, Oracle, or a SQLite file. Every loader returns the same
shape so the rest of the app is database-agnostic.

Shape of a returned schema dict (same as sql_import.parse_sql_schema output):
    {success, tablesData, fkList, tableCount, fkCount, dialect, source, warnings}
"""

import time
import sqlite3
import sqlglot

import oracle_sync
from sql_import import parse_sql_schema

SUPPORTED = {
    "oracle": {
        "label_ar": "Oracle",
        "label_en": "Oracle",
        "fields": ["host", "port", "service_name", "user", "password"],
        "defaults": {"host": "localhost", "port": 1521, "service_name": "orclpdb"},
    },
    "mysql": {
        "label_ar": "MySQL",
        "label_en": "MySQL",
        "fields": ["host", "port", "database", "user", "password"],
        "defaults": {"host": "localhost", "port": 3306, "database": ""},
    },
    "postgres": {
        "label_ar": "PostgreSQL",
        "label_en": "PostgreSQL",
        "fields": ["host", "port", "database", "user", "password"],
        "defaults": {"host": "localhost", "port": 5432, "database": ""},
    },
    "sqlite_file": {
        "label_ar": "ملف SQLite (.db/.sqlite)",
        "label_en": "SQLite file (.db/.sqlite)",
        "fields": ["path"],
        "defaults": {"path": ""},
    },
}

# Driver availability ---------------------------------------------------------
_DRIVERS = {}


def _check_driver(name):
    if name not in _DRIVERS:
        try:
            __import__(name)
            _DRIVERS[name] = True
        except ImportError:
            _DRIVERS[name] = False
    return _DRIVERS[name]


SUPPORTED["mysql"]["available"] = _check_driver("pymysql")
SUPPORTED["postgres"]["available"] = _check_driver("psycopg2")
SUPPORTED["oracle"]["available"] = _check_driver("oracledb")
SUPPORTED["sqlite_file"]["available"] = True


# ---------------------------------------------------------------------------
# MySQL
# ---------------------------------------------------------------------------
def _load_mysql(params):
    import pymysql

    conn = pymysql.connect(
        host=params.get("host", "localhost"),
        port=int(params.get("port", 3306) or 3306),
        user=params.get("user", ""),
        password=params.get("password", "") or "",
        database=params.get("database", "") or None,
        charset="utf8mb4",
        connect_timeout=8,
    )
    tables_data = {}
    fk_map = {}  # child -> list of dicts
    fk_order = []  # preserve discovery order
    try:
        cur = conn.cursor()
        db = params.get("database", "") or conn.db
        cur.execute(
            "SELECT TABLE_NAME FROM information_schema.tables "
            "WHERE table_schema=%s AND table_type='BASE TABLE' ORDER BY TABLE_NAME",
            (db,),
        )
        tables = [r[0] for r in cur.fetchall()]

        # columns
        cur.execute(
            "SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, IS_NULLABLE "
            "FROM information_schema.columns WHERE table_schema=%s "
            "ORDER BY TABLE_NAME, ORDINAL_POSITION",
            (db,),
        )
        cols_partition = {}
        for tbl, col, dtype, ctype, nullable in cur.fetchall():
            if tbl not in tables:
                continue
            display = (ctype or dtype).lower()
            cols_partition.setdefault(tbl, []).append({
                "name": col, "type": display,
                "nullable": nullable and nullable.upper() == "YES",
            })

        # primary keys
        cur.execute(
            "SELECT TABLE_NAME, COLUMN_NAME FROM information_schema.key_column_usage "
            "WHERE table_schema=%s AND constraint_name='PRIMARY' "
            "ORDER BY TABLE_NAME, ORDINAL_POSITION",
            (db,),
        )
        pk_partition = {}
        for tbl, col in cur.fetchall():
            pk_partition.setdefault(tbl, []).append(col)

        # foreign keys
        cur.execute(
            "SELECT CONSTRAINT_NAME, TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME "
            "FROM information_schema.key_column_usage "
            "WHERE table_schema=%s AND REFERENCED_TABLE_NAME IS NOT NULL "
            "ORDER BY CONSTRAINT_NAME, ORDINAL_POSITION",
            (db,),
        )
        for fk, child, ccol, parent, pcol in cur.fetchall():
            if child not in tables or parent not in tables:
                continue
            entry = None
            if fk in fk_order:
                entry = fk_map[fk]
            else:
                fk_order.append(fk)
                entry = {"child": child, "parent": parent, "fk": fk, "cols": []}
                fk_map[fk] = entry
            entry["cols"].append(ccol)

        for tbl in tables:
            tables_data[tbl] = {
                "columns": cols_partition.get(tbl, []),
                "pks": pk_partition.get(tbl, []),
            }
        fk_list = [{"child": e["child"], "parent": e["parent"], "fk": e["fk"],
                    "cols": ", ".join(e["cols"])} for e in fk_map.values()]
        conn.close()
        return _schema_result(tables_data, fk_list, "mysql", "mysql")
    except Exception:
        conn.close()
        raise


# ---------------------------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------------------------
_PG_TYPE_ALIAS = {
    "character varying": "varchar", "character": "char", "numeric": "numeric",
    "integer": "int", "bigint": "bigint", "smallint": "smallint",
    "timestamp without time zone": "timestamp",
    "timestamp with time zone": "timestamptz",
    "date": "date", "time without time zone": "time",
    "boolean": "boolean", "double precision": "float8",
    "real": "float4", "text": "text", "bytea": "bytea", "uuid": "uuid",
}


def _load_postgres(params, schema="public"):
    import psycopg2

    conn = psycopg2.connect(
        host=params.get("host", "localhost"),
        port=int(params.get("port", 5432) or 5432),
        user=params.get("user", ""),
        password=params.get("password", "") or "",
        dbname=params.get("database", "") or None,
        connect_timeout=8,
    )
    tables_data = {}
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname=%s ORDER BY tablename",
            (schema,),
        )
        tables = [r[0] for r in cur.fetchall()]

        cur.execute(
            "SELECT table_name, column_name, data_type, is_nullable "
            "FROM information_schema.columns WHERE table_schema=%s "
            "ORDER BY table_name, ordinal_position",
            (schema,),
        )
        cols_partition = {}
        for tbl, col, dtype, nullable in cur.fetchall():
            if tbl not in tables:
                continue
            if dtype == "ARRAY":
                dtype = "array"
            display = _PG_TYPE_ALIAS.get(dtype, dtype)
            cols_partition.setdefault(tbl, []).append({
                "name": col, "type": display,
                "nullable": nullable.upper() == "YES",
            })

        cur.execute(
            "SELECT tc.table_name, kcu.column_name "
            "FROM information_schema.table_constraints tc "
            "JOIN information_schema.key_column_usage kcu "
            "  ON tc.constraint_name=kcu.constraint_name AND tc.constraint_schema=kcu.constraint_schema "
            "WHERE tc.constraint_type='PRIMARY KEY' AND tc.table_schema=%s "
            "ORDER BY tc.table_name, kcu.ordinal_position",
            (schema,),
        )
        pk_partition = {}
        for tbl, col in cur.fetchall():
            pk_partition.setdefault(tbl, []).append(col)

        cur.execute(
            "SELECT tc.constraint_name, kcu.table_name, kcu.column_name, "
            "       ccu.table_name, ccu.column_name "
            "FROM information_schema.table_constraints tc "
            "JOIN information_schema.key_column_usage kcu "
            "  ON tc.constraint_name=kcu.constraint_name AND tc.constraint_schema=kcu.constraint_schema "
            "JOIN information_schema.constraint_column_usage ccu "
            "  ON tc.constraint_name=ccu.constraint_name AND tc.constraint_schema=ccu.constraint_schema "
            "WHERE tc.constraint_type='FOREIGN KEY' AND tc.table_schema=%s "
            "ORDER BY tc.constraint_name, kcu.ordinal_position",
            (schema,),
        )
        fk_map = {}
        fk_order = []
        for fk, child, ccol, parent, pcol in cur.fetchall():
            if child not in tables or parent not in tables:
                continue
            if fk not in fk_order:
                fk_order.append(fk)
                fk_map[fk] = {"child": child, "parent": parent, "fk": fk, "cols": []}
            fk_map[fk]["cols"].append(ccol)

        for tbl in tables:
            tables_data[tbl] = {
                "columns": cols_partition.get(tbl, []),
                "pks": pk_partition.get(tbl, []),
            }
        fk_list = [{"child": e["child"], "parent": e["parent"], "fk": e["fk"],
                    "cols": ", ".join(e["cols"])} for e in fk_map.values()]
        conn.close()
        return _schema_result(tables_data, fk_list, "postgres", "postgres")
    except Exception:
        conn.close()
        raise


# ---------------------------------------------------------------------------
# SQLite file (reuses the general SQL parser on the live DDL)
# ---------------------------------------------------------------------------
def _load_sqlite_file(params):
    path = params.get("path", "")
    if not path:
        raise ValueError("SQLite file path is required")
    conn = sqlite3.connect(path)
    ddl_parts = []
    try:
        for (tbl,) in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall():
            row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (tbl,)).fetchone()
            if row and row[0]:
                ddl_parts.append(row[0] + ";")
        conn.close()
    except Exception:
        conn.close()
        raise
    if not ddl_parts:
        raise ValueError("No user tables found in the SQLite file")
    sql_text = "\n\n".join(ddl_parts)
    return parse_sql_schema(sql_text, dialect="sqlite")


# ---------------------------------------------------------------------------
# Oracle (reuses existing loader, normalized)
# ---------------------------------------------------------------------------
def _load_oracle(params):
    user = params.get("user")
    password = params.get("password")
    host = params.get("host", "localhost")
    port = int(params.get("port", 1521) or 1521)
    service = params.get("service_name", "orclpdb")
    dsn = f"{host}:{port}/{service}"
    res = oracle_sync.sync_raw_schema(user=user, password=password, dsn=dsn)
    return _schema_result(res["tablesData"], res["fkList"], "oracle", "oracle")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _schema_result(tables_data, fk_list, dialect, source):
    return {
        "success": True,
        "tablesData": tables_data,
        "fkList": fk_list,
        "tableCount": len(tables_data),
        "fkCount": len(fk_list),
        "dialect": dialect,
        "source": source,
        "warnings": [],
    }


def list_connectors():
    out = []
    for key, meta in SUPPORTED.items():
        out.append({"key": key, **{k: v for k, v in meta.items() if k != "defaults"}})
    return out


def test_connection(dialect, params):
    start = time.time()
    try:
        res = connect(dialect, params)
        elapsed = round((time.time() - start) * 1000, 2)
        return {
            "success": True,
            "latencyMs": elapsed,
            "tablesFound": res["tableCount"],
            "fksFound": res["fkCount"],
            "dialect": res["dialect"],
        }
    except Exception as e:
        elapsed = round((time.time() - start) * 1000, 2)
        return {"success": False, "latencyMs": elapsed, "error": str(e)}


def connect(dialect, params):
    """Connect to a live database and return the unified schema dict."""
    params = dict(params or {})
    if dialect == "mysql":
        return _load_mysql(params)
    if dialect == "postgres":
        return _load_postgres(params)
    if dialect == "oracle":
        return _load_oracle(params)
    if dialect == "sqlite_file":
        return _load_sqlite_file(params)
    raise ValueError(f"Unsupported dialect: {dialect}")