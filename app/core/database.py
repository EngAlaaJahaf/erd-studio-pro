import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "app.db")

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # 1. Settings Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at TEXT
    )
    """)

    # 2. Table States (Positions & Custom Column Overrides)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS table_states (
        table_name TEXT PRIMARY KEY,
        pos_x REAL NOT NULL,
        pos_y REAL NOT NULL,
        is_visible INTEGER NOT NULL DEFAULT 1,
        custom_hidden_cols TEXT DEFAULT '[]',
        updated_at TEXT
    )
    """)

    # 3. Saved Layout Presets
    cur.execute("""
    CREATE TABLE IF NOT EXISTS saved_layouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        view_mode TEXT DEFAULT 'no-audit',
        theme TEXT DEFAULT 'mermaid',
        positions_json TEXT NOT NULL,
        hidden_cols_json TEXT NOT NULL,
        selected_tables_json TEXT NOT NULL,
        created_at TEXT,
        updated_at TEXT
    )
    """)

    # 4. Cached Schema Metadata
    cur.execute("""
    CREATE TABLE IF NOT EXISTS schema_cache (
        id INTEGER PRIMARY KEY,
        tables_data_json TEXT NOT NULL,
        fk_list_json TEXT NOT NULL,
        table_count INTEGER NOT NULL,
        fk_count INTEGER NOT NULL,
        last_sync_time TEXT NOT NULL
    )
    """)

    # 5. Subsystem Mappings (smart schema classification)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS subsystem_mappings (
        table_name TEXT PRIMARY KEY,
        subsystem_key TEXT NOT NULL,
        updated_at TEXT
    )
    """)

    # 5b. Subsystem definitions (custom names/colors, e.g. from AI classification)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS subsystem_defs (
        key TEXT PRIMARY KEY,
        name_ar TEXT,
        name_en TEXT,
        description_ar TEXT,
        description_en TEXT,
        color TEXT,
        sort_order INTEGER,
        updated_at TEXT
    )
    """)

    # 6. AI Chat History
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT
    )
    """)

    # 7. Enterprise Audit Trail (Immutable Events Log)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_log_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        severity TEXT DEFAULT 'INFO',
        actor TEXT DEFAULT 'SYSTEM',
        dialect TEXT,
        target_db TEXT,
        details_json TEXT,
        snapshot_id INTEGER,
        created_at TEXT NOT NULL
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log_events(created_at DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_type ON audit_log_events(event_type)")

    # 8. Schema Snapshots (Historical Versions / Time Machine)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS schema_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_name TEXT NOT NULL,
        description TEXT,
        trigger_event TEXT NOT NULL,
        tables_data_json TEXT NOT NULL,
        fk_list_json TEXT NOT NULL,
        table_count INTEGER NOT NULL,
        fk_count INTEGER NOT NULL,
        dialect TEXT DEFAULT 'oracle',
        source TEXT,
        fingerprint TEXT,
        created_at TEXT NOT NULL
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_created ON schema_snapshots(created_at DESC)")

    conn.commit()

    # --- Migration: schema_cache metadata columns ---
    cols = {r[1] for r in conn.execute("PRAGMA table_info(schema_cache)").fetchall()}
    if "dialect" not in cols:
        conn.execute("ALTER TABLE schema_cache ADD COLUMN dialect TEXT DEFAULT 'oracle'")
    if "source" not in cols:
        conn.execute("ALTER TABLE schema_cache ADD COLUMN source TEXT DEFAULT 'oracle'")
    if "schema_name" not in cols:
        conn.execute("ALTER TABLE schema_cache ADD COLUMN schema_name TEXT")
    if "schema_fingerprint" not in cols:
        conn.execute("ALTER TABLE schema_cache ADD COLUMN schema_fingerprint TEXT")

    # --- Migration: add width/height columns to table_states ---
    cols = {r[1] for r in conn.execute("PRAGMA table_info(table_states)").fetchall()}
    if "pos_w" not in cols:
        conn.execute("ALTER TABLE table_states ADD COLUMN pos_w REAL DEFAULT 270")
    if "pos_h" not in cols:
        conn.execute("ALTER TABLE table_states ADD COLUMN pos_h REAL DEFAULT 0")
    conn.commit()

    # Seed Default Settings if not present
    defaults = {
        "current_theme": "mermaid",
        "current_lang": "ar",
        "global_view_mode": "no-audit",
        "is_sidebar_collapsed": "0",
        "zoom": "0.82",
        "pan_x": "40",
        "pan_y": "40",
        "oracle_dsn": "localhost:1521/orclpdb",
        "oracle_user": "TESTR",
        "oracle_password": "TESTR",
        "auto_save": "1",
        "db_host": "localhost",
        "db_port": "1521",
        "db_service": "orclpdb",
        "db_user": "TESTR",
        "db_password": "TESTR",
        "db_dialect": "oracle",
        "db_file": "",
        "ai_provider": "local",
        "ai_base_url": "https://api.openai.com/v1",
        "ai_api_key": "",
        "ai_model": "gpt-4o-mini",
        "ai_temperature": "0.4"
    }
    now = datetime.now().isoformat()
    for k, v in defaults.items():
        cur.execute("INSERT OR IGNORE INTO app_settings (key, value, updated_at) VALUES (?, ?, ?)", (k, v, now))
    conn.commit()
    conn.close()

# --- Settings CRUD ---
def get_all_settings():
    conn = get_connection()
    rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}

def set_setting(key, value):
    conn = get_connection()
    now = datetime.now().isoformat()
    conn.execute("INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (key, str(value), now))
    conn.commit()
    conn.close()

def update_bulk_settings(settings_dict):
    conn = get_connection()
    now = datetime.now().isoformat()
    for k, v in settings_dict.items():
        conn.execute("INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (k, str(v), now))
    conn.commit()
    conn.close()

# --- Table States (Live Positions & Column Preferences) ---
def get_all_table_states():
    conn = get_connection()
    rows = conn.execute("SELECT table_name, pos_x, pos_y, pos_w, pos_h, is_visible, custom_hidden_cols FROM table_states").fetchall()
    conn.close()
    positions = {}
    hidden_cols = {}
    visible_tables = []
    for r in rows:
        positions[r["table_name"]] = {
            "x": r["pos_x"],
            "y": r["pos_y"],
            "width": r["pos_w"] if r["pos_w"] else 270,
            "height": r["pos_h"] if r["pos_h"] else 0
        }
        if r["is_visible"]:
            visible_tables.append(r["table_name"])
        try:
            hidden = json.loads(r["custom_hidden_cols"])
            if hidden:
                hidden_cols[r["table_name"]] = hidden
        except:
            pass
    return {
        "positions": positions,
        "hidden_cols": hidden_cols,
        "visible_tables": visible_tables
    }

def save_all_table_states(positions, hidden_cols=None, visible_tables=None):
    conn = get_connection()
    now = datetime.now().isoformat()
    hidden_cols = hidden_cols or {}
    visible_set = set(visible_tables) if visible_tables is not None else None

    # Prune obsolete tables from table_states if schema is known
    cached_row = conn.execute("SELECT tables_data_json FROM schema_cache WHERE id=1").fetchone()
    if cached_row and cached_row[0]:
        try:
            valid_set = set(json.loads(cached_row[0]).keys())
            if valid_set:
                placeholders = ','.join('?' for _ in valid_set)
                conn.execute(f"DELETE FROM table_states WHERE table_name NOT IN ({placeholders})", list(valid_set))
        except Exception:
            pass

    for tbl, pos in positions.items():
        x = pos.get("x", 100)
        y = pos.get("y", 100)
        w = float(pos.get("width", 270)) if pos.get("width") else 270
        h = float(pos.get("height", 0)) if pos.get("height") else 0
        is_vis = 1 if (visible_set is None or tbl in visible_set) else 0
        h_cols = json.dumps(hidden_cols.get(tbl, []))
        conn.execute("""
        INSERT INTO table_states (table_name, pos_x, pos_y, pos_w, pos_h, is_visible, custom_hidden_cols, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(table_name) DO UPDATE SET
            pos_x=excluded.pos_x,
            pos_y=excluded.pos_y,
            pos_w=excluded.pos_w,
            pos_h=excluded.pos_h,
            is_visible=excluded.is_visible,
            custom_hidden_cols=excluded.custom_hidden_cols,
            updated_at=excluded.updated_at
        """, (tbl, x, y, w, h, is_vis, h_cols, now))
    conn.commit()
    conn.close()

# --- Schema Cache ---
def get_cached_schema():
    conn = get_connection()
    row = conn.execute(
        "SELECT tables_data_json, fk_list_json, table_count, fk_count, last_sync_time, "
        "       COALESCE(dialect,'oracle') AS dialect, COALESCE(source,'oracle') AS source, schema_name, schema_fingerprint "
        "FROM schema_cache WHERE id=1"
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "tablesData": json.loads(row["tables_data_json"]),
        "fkList": json.loads(row["fk_list_json"]),
        "tableCount": row["table_count"],
        "fkCount": row["fk_count"],
        "lastSync": row["last_sync_time"],
        "dialect": row["dialect"],
        "source": row["source"],
        "schemaName": row["schema_name"],
        "schemaFingerprint": row["schema_fingerprint"],
    }

def save_schema_cache(tables_data, fk_list, dialect="oracle", source="oracle", schema_name=None, fingerprint=None):
    conn = get_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    td_json = json.dumps(tables_data, ensure_ascii=False)
    fk_json = json.dumps(fk_list, ensure_ascii=False)
    t_count = len(tables_data)
    fk_count = len(fk_list)
    conn.execute("""
    INSERT INTO schema_cache (id, tables_data_json, fk_list_json, table_count, fk_count, last_sync_time, dialect, source, schema_name, schema_fingerprint)
    VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        tables_data_json=excluded.tables_data_json,
        fk_list_json=excluded.fk_list_json,
        table_count=excluded.table_count,
        fk_count=excluded.fk_count,
        last_sync_time=excluded.last_sync_time,
        dialect=excluded.dialect,
        source=excluded.source,
        schema_name=excluded.schema_name,
        schema_fingerprint=excluded.schema_fingerprint
    """, (td_json, fk_json, t_count, fk_count, now, dialect, source, schema_name, fingerprint))
    conn.commit()
    conn.close()

def reset_for_new_schema():
    """Clear everything derived from the previous schema (positions, layouts,
    subsystem classifications, chat history). Settings are preserved."""
    conn = get_connection()
    conn.execute("DELETE FROM table_states")
    conn.execute("DELETE FROM saved_layouts")
    conn.execute("DELETE FROM subsystem_mappings")
    conn.execute("DELETE FROM subsystem_defs")
    conn.execute("DELETE FROM chat_messages")
    conn.commit()
    conn.close()

def clear_schema_cache():
    """Permanently delete cached schema, positions, layouts, subsystem mappings and definitions."""
    conn = get_connection()
    conn.execute("DELETE FROM schema_cache")
    conn.execute("DELETE FROM table_states")
    conn.execute("DELETE FROM saved_layouts")
    conn.execute("DELETE FROM subsystem_mappings")
    conn.execute("DELETE FROM subsystem_defs")
    conn.commit()
    conn.close()


# --- Named Saved Layouts ---
def get_all_layouts():
    conn = get_connection()
    rows = conn.execute("SELECT id, name, description, view_mode, theme, created_at, updated_at FROM saved_layouts ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_layout_by_name_or_id(layout_id_or_name):
    conn = get_connection()
    if isinstance(layout_id_or_name, int) or layout_id_or_name.isdigit():
        row = conn.execute("SELECT * FROM saved_layouts WHERE id=?", (int(layout_id_or_name),)).fetchone()
    else:
        row = conn.execute("SELECT * FROM saved_layouts WHERE name=?", (layout_id_or_name,)).fetchone()
    conn.close()
    if not row:
        return None
    res = dict(row)
    res["positions"] = json.loads(res["positions_json"])
    res["hidden_cols"] = json.loads(res["hidden_cols_json"])
    res["selected_tables"] = json.loads(res["selected_tables_json"])
    return res

def save_layout_preset(name, positions, hidden_cols, selected_tables, view_mode="no-audit", theme="mermaid", description=""):
    conn = get_connection()
    now = datetime.now().isoformat()
    pos_json = json.dumps(positions, ensure_ascii=False)
    h_json = json.dumps(hidden_cols, ensure_ascii=False)
    sel_json = json.dumps(selected_tables, ensure_ascii=False)
    conn.execute("""
    INSERT INTO saved_layouts (name, description, view_mode, theme, positions_json, hidden_cols_json, selected_tables_json, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(name) DO UPDATE SET
        description=excluded.description,
        view_mode=excluded.view_mode,
        theme=excluded.theme,
        positions_json=excluded.positions_json,
        hidden_cols_json=excluded.hidden_cols_json,
        selected_tables_json=excluded.selected_tables_json,
        updated_at=excluded.updated_at
    """, (name, description, view_mode, theme, pos_json, h_json, sel_json, now, now))
    conn.commit()
    conn.close()

def delete_layout_preset(name_or_id):
    conn = get_connection()
    if isinstance(name_or_id, int) or name_or_id.isdigit():
        conn.execute("DELETE FROM saved_layouts WHERE id=?", (int(name_or_id),))
    else:
        conn.execute("DELETE FROM saved_layouts WHERE name=?", (name_or_id,))
    conn.commit()
    conn.close()

# --- Factory Reset ---
def factory_reset():
    """Reset all user data to defaults, preserving schema cache."""
    conn = get_connection()
    now = datetime.now().isoformat()

    # Clear all table states
    conn.execute("DELETE FROM table_states")

    # Clear all saved layouts
    conn.execute("DELETE FROM saved_layouts")

    # Reset app_settings to defaults
    conn.execute("DELETE FROM app_settings")
    defaults = {
        "current_theme": "mermaid",
        "current_lang": "ar",
        "global_view_mode": "no-audit",
        "is_sidebar_collapsed": "0",
        "zoom": "0.82",
        "pan_x": "40",
        "pan_y": "40",
        "oracle_dsn": "localhost:1521/orclpdb",
        "oracle_user": "TESTR",
        "oracle_password": "TESTR",
        "auto_save": "1",
        "db_host": "localhost",
        "db_port": "1521",
        "db_service": "orclpdb",
        "db_user": "TESTR",
        "db_password": "TESTR",
        "db_dialect": "oracle",
        "db_file": "",
        "ai_provider": "local",
        "ai_base_url": "https://api.openai.com/v1",
        "ai_api_key": "",
        "ai_model": "gpt-4o-mini",
        "ai_temperature": "0.4"
    }
    for k, v in defaults.items():
        conn.execute("INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?)", (k, v, now))

    conn.commit()
    conn.close()

# --- Subsystem Mappings ---
def get_subsystem_mappings():
    conn = get_connection()
    rows = conn.execute("SELECT table_name, subsystem_key FROM subsystem_mappings").fetchall()
    conn.close()
    return {r["table_name"]: r["subsystem_key"] for r in rows}

def save_subsystem_mappings(mapping):
    conn = get_connection()
    now = datetime.now().isoformat()
    for tbl, key in mapping.items():
        conn.execute("""
        INSERT INTO subsystem_mappings (table_name, subsystem_key, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(table_name) DO UPDATE SET subsystem_key=excluded.subsystem_key, updated_at=excluded.updated_at
        """, (tbl, key, now))
    conn.commit()
    conn.close()

def get_subsystem_defs():
    conn = get_connection()
    rows = conn.execute(
        "SELECT key, name_ar, name_en, description_ar, description_en, color, sort_order "
        "FROM subsystem_defs ORDER BY COALESCE(sort_order, 999), key"
    ).fetchall()
    conn.close()
    if not rows:
        return None
    return {
        r["key"]: {
            "key": r["key"],
            "name_ar": r["name_ar"] or r["key"],
            "name_en": r["name_en"] or r["key"],
            "description_ar": r["description_ar"] or "",
            "description_en": r["description_en"] or "",
            "color": r["color"] or "#64748b",
        }
        for r in rows
    }

def save_subsystem_defs(defs):
    conn = get_connection()
    now = datetime.now().isoformat()
    for i, d in enumerate(defs):
        conn.execute("""
        INSERT INTO subsystem_defs (key, name_ar, name_en, description_ar, description_en, color, sort_order, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            name_ar=excluded.name_ar,
            name_en=excluded.name_en,
            description_ar=excluded.description_ar,
            description_en=excluded.description_en,
            color=excluded.color,
            sort_order=excluded.sort_order,
            updated_at=excluded.updated_at
        """, (d["key"], d.get("name_ar", d["key"]), d.get("name_en", d["key"]),
              d.get("description_ar", ""), d.get("description_en", ""),
              d.get("color", "#64748b"), i, now))
    conn.commit()
    conn.close()

def clear_subsystem_defs():
    conn = get_connection()
    conn.execute("DELETE FROM subsystem_defs")
    conn.commit()
    conn.close()

# --- AI Chat History ---
def get_chat_history(limit=60):
    conn = get_connection()
    rows = conn.execute("SELECT role, content FROM chat_messages ORDER BY id ASC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_chat_message(role, content):
    conn = get_connection()
    now = datetime.now().isoformat()
    conn.execute("INSERT INTO chat_messages (role, content, created_at) VALUES (?, ?, ?)", (role, content, now))
    conn.commit()
    conn.close()

def clear_chat_history():
    conn = get_connection()
    conn.execute("DELETE FROM chat_messages")
    conn.commit()
    conn.close()


# --- Enterprise Audit Trail & Historical Snapshots ---

def record_audit_event(
    event_type: str,
    title: str,
    description: str = None,
    severity: str = "INFO",
    actor: str = "SYSTEM",
    dialect: str = None,
    target_db: str = None,
    details: dict = None,
    snapshot_id: int = None
) -> int:
    conn = get_connection()
    now = datetime.now().isoformat()
    cur = conn.cursor()
    details_str = json.dumps(details, ensure_ascii=False) if details else None
    cur.execute("""
        INSERT INTO audit_log_events 
        (event_type, title, description, severity, actor, dialect, target_db, details_json, snapshot_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (event_type, title, description, severity, actor, dialect, target_db, details_str, snapshot_id, now))
    event_id = cur.lastrowid
    conn.commit()
    conn.close()
    return event_id

def get_audit_events(limit: int = 100, offset: int = 0, event_type: str = None, severity: str = None, search: str = None):
    conn = get_connection()
    query = "SELECT * FROM audit_log_events WHERE 1=1"
    params = []
    if event_type and event_type != "ALL":
        query += " AND event_type = ?"
        params.append(event_type)
    if severity and severity != "ALL":
        query += " AND severity = ?"
        params.append(severity)
    if search:
        query += " AND (title LIKE ? OR description LIKE ? OR target_db LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s])
    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    events = []
    for r in rows:
        d = dict(r)
        if d.get("details_json"):
            try:
                d["details"] = json.loads(d["details_json"])
            except Exception:
                d["details"] = {}
        else:
            d["details"] = {}
        events.append(d)
    conn.close()
    return events

def count_audit_events(event_type: str = None, severity: str = None, search: str = None) -> int:
    conn = get_connection()
    query = "SELECT COUNT(*) FROM audit_log_events WHERE 1=1"
    params = []
    if event_type and event_type != "ALL":
        query += " AND event_type = ?"
        params.append(event_type)
    if severity and severity != "ALL":
        query += " AND severity = ?"
        params.append(severity)
    if search:
        query += " AND (title LIKE ? OR description LIKE ? OR target_db LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s])
    count = conn.execute(query, params).fetchone()[0]
    conn.close()
    return count

def get_audit_stats():
    conn = get_connection()
    total_events = conn.execute("SELECT COUNT(*) FROM audit_log_events").fetchone()[0]
    total_snapshots = conn.execute("SELECT COUNT(*) FROM schema_snapshots").fetchone()[0]
    live_migrations = conn.execute("SELECT COUNT(*) FROM audit_log_events WHERE event_type = 'MIGRATION_LIVE'").fetchone()[0]
    last_event = conn.execute("SELECT created_at, event_type, title, severity FROM audit_log_events ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return {
        "totalEvents": total_events,
        "total_events": total_events,
        "totalSnapshots": total_snapshots,
        "snapshots_count": total_snapshots,
        "liveMigrations": live_migrations,
        "live_migrations_count": live_migrations,
        "lastEvent": dict(last_event) if last_event else None,
        "last_event": dict(last_event) if last_event else None
    }

def clear_audit_events(keep_latest: int = 50):
    conn = get_connection()
    if keep_latest > 0:
        conn.execute("""
            DELETE FROM audit_log_events 
            WHERE id NOT IN (SELECT id FROM audit_log_events ORDER BY id DESC LIMIT ?)
        """, (keep_latest,))
    else:
        conn.execute("DELETE FROM audit_log_events")
    conn.commit()
    conn.close()

def create_schema_snapshot(
    name: str,
    tables_data: dict,
    fk_list: list,
    trigger_event: str = "MANUAL",
    description: str = None,
    dialect: str = "oracle",
    source: str = None,
    fingerprint: str = None
) -> int:
    conn = get_connection()
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO schema_snapshots
        (snapshot_name, description, trigger_event, tables_data_json, fk_list_json, table_count, fk_count, dialect, source, fingerprint, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name,
        description,
        trigger_event,
        json.dumps(tables_data or {}, ensure_ascii=False),
        json.dumps(fk_list or [], ensure_ascii=False),
        len(tables_data or {}),
        len(fk_list or []),
        dialect or "oracle",
        source or "canvas",
        fingerprint or "",
        now
    ))
    snap_id = cur.lastrowid
    conn.commit()
    conn.close()
    return snap_id

def get_schema_snapshots(limit: int = 50):
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, snapshot_name, description, trigger_event, table_count, fk_count, dialect, source, fingerprint, created_at
        FROM schema_snapshots ORDER BY id DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["name"] = d.get("snapshot_name")
        result.append(d)
    return result

def get_schema_snapshot_by_id(snapshot_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM schema_snapshots WHERE id = ?", (snapshot_id,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["name"] = d.get("snapshot_name")
    try:
        d["tablesData"] = json.loads(d["tables_data_json"])
    except Exception:
        d["tablesData"] = {}
    try:
        d["fkList"] = json.loads(d["fk_list_json"])
    except Exception:
        d["fkList"] = []
    return d

def delete_schema_snapshot(snapshot_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM schema_snapshots WHERE id = ?", (snapshot_id,))
    deleted = cur.rowcount > 0
    cur.execute("UPDATE audit_log_events SET snapshot_id = NULL WHERE snapshot_id = ?", (snapshot_id,))
    conn.commit()
    conn.close()
    return deleted

