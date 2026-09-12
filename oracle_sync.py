import oracledb
import logging
from database import get_all_settings, save_schema_cache, get_cached_schema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("oracle_sync")


def fetch_schema(user=None, password=None, dsn=None, table_filter=None):
    """Connect to Oracle, introspect ALL user tables and return the unified
    schema model {tablesData, fkList, tableCount, fkCount}.

    table_filter: optional SQL predicate (string) added to the table listing
    query, e.g. "(table_name LIKE 'COM_%' OR table_name LIKE 'RAF_%')".
    """
    settings = get_all_settings()
    db_user = user or settings.get("oracle_user", "TESTR")
    db_pwd = password or settings.get("oracle_password", "TESTR")
    db_dsn = dsn or settings.get("oracle_dsn", "localhost:1521/orclpdb")

    logger.info(f"Connecting to Oracle DB: {db_user}@{db_dsn}")
    conn = oracledb.connect(user=db_user, password=db_pwd, dsn=db_dsn)
    cur = conn.cursor()
    owner = db_user.upper()

    # 1. Fetch all tables (optionally filtered)
    if table_filter:
        sql = f"SELECT table_name FROM all_tables WHERE owner=:owner AND {table_filter} ORDER BY table_name"
    else:
        sql = "SELECT table_name FROM all_tables WHERE owner=:owner ORDER BY table_name"
    cur.execute(sql, owner=owner)
    tables = [r[0] for r in cur.fetchall()]

    # 2. Fetch Columns and Primary Keys
    tables_data = {}
    for t in tables:
        cur.execute("""
            SELECT column_name, data_type, data_length, nullable
            FROM all_tab_columns
            WHERE owner=:owner AND table_name=:t
            ORDER BY column_id
        """, owner=owner, t=t)
        cols = []
        for col, dtype, dlen, nullable in cur.fetchall():
            disp = _display_type(dtype, dlen)
            cols.append({"name": col, "type": disp, "nullable": nullable})

        cur.execute("""
            SELECT cols.column_name
            FROM all_constraints cons
            JOIN all_cons_columns cols ON cons.constraint_name=cols.constraint_name AND cons.owner=cols.owner
            WHERE cons.owner=:owner AND cons.table_name=:t AND cons.constraint_type='P'
            ORDER BY cols.position
        """, owner=owner, t=t)
        pks = [r[0] for r in cur.fetchall()]
        tables_data[t] = {"columns": cols, "pks": pks}

    # 3. Fetch Foreign Key Relationships
    cur.execute("""
        SELECT
            ac.table_name as child_table,
            ac.constraint_name as fk_name,
            ac.r_constraint_name,
            ac.r_owner,
            LISTAGG(acc.column_name, ', ') WITHIN GROUP (ORDER BY acc.position) as fk_cols
        FROM all_constraints ac
        JOIN all_cons_columns acc ON ac.constraint_name=acc.constraint_name AND ac.owner=acc.owner
        WHERE ac.owner=:owner AND ac.constraint_type='R'
        GROUP BY ac.table_name, ac.constraint_name, ac.r_constraint_name, ac.r_owner
    """, owner=owner)
    raw_fks = cur.fetchall()

    fk_list = []
    for child, fk_name, r_cons, r_owner, fk_cols in raw_fks:
        cur.execute("SELECT table_name FROM all_constraints WHERE constraint_name=:c AND owner=:o", c=r_cons, o=r_owner)
        row = cur.fetchone()
        parent = row[0] if row else None
        if parent and parent in tables and child in tables:
            fk_list.append({"child": child, "parent": parent, "fk": fk_name, "cols": fk_cols})

    conn.close()
    logger.info(f"Extracted {len(tables_data)} tables, {len(fk_list)} FK constraints")
    return {
        "tablesData": tables_data,
        "fkList": fk_list,
        "tableCount": len(tables_data),
        "fkCount": len(fk_list),
    }


def _display_type(dtype, dlen):
    if dtype == 'VARCHAR2':
        return f"VARCHAR2({dlen})"
    if dtype == 'NVARCHAR2':
        return f"NVARCHAR2({dlen//2})"
    if dtype == 'NUMBER':
        return "NUMBER"
    if dtype.startswith('TIMESTAMP'):
        return "TIMESTAMP"
    if dtype == 'DATE':
        return "DATE"
    if dtype in ('CLOB', 'BLOB'):
        return dtype
    return dtype


def sync_raw_schema(user=None, password=None, dsn=None):
    """Pure schema load (no cache write) - used by generic connectors."""
    return fetch_schema(user=user, password=password, dsn=dsn)


def sync_schema_from_oracle(user=None, password=None, dsn=None, table_filter=None):
    """Legacy entry point: load + write SQLite cache + return enriched result."""
    try:
        res = fetch_schema(user=user, password=password, dsn=dsn, table_filter=table_filter)
        save_schema_cache(res["tablesData"], res["fkList"])
        return {"success": True, **res}
    except Exception as e:
        logger.error(f"Oracle Sync failed: {e}")
        cached = get_cached_schema()
        if cached:
            return {"success": False, "error": str(e), "cached": cached}
        raise e


if __name__ == "__main__":
    from database import init_db
    init_db()
    res = sync_schema_from_oracle()
    print("Sync Result:", res["success"], f"Tables: {res.get('tableCount')}, FKs: {res.get('fkCount')}")