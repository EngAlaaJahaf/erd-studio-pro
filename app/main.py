import os
import re
import uvicorn
import json
import hashlib
import time
from fastapi import FastAPI, HTTPException, Body, UploadFile, File as FileParam, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, Response
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import oracledb

from app.core import database as db
from app.core import oracle_sync
from app.core import subsystems as subsys
from app.ai import ai_assistant
from app.ai import ai_classify
from app.connectors import db_connectors
from app.services import sql_import
from app.services import sql_export
from app.services import datadict_import
from app.services import datadict_export

# Initialize SQLite Database
db.init_db()

# Check if schema cache exists, if not, sync from Oracle
if not db.get_cached_schema():
    try:
        oracle_sync.sync_schema_from_oracle()
    except Exception as e:
        print(f"Initial sync warning: {e}")

# Seed subsystem classification if no saved mapping yet
try:
    if not db.get_subsystem_mappings():
        cached = db.get_cached_schema()
        if cached:
            res = subsys.detect_subsystems(cached["tablesData"], cached["fkList"])
            db.save_subsystem_mappings(res["mapping"])
            db.save_subsystem_defs(res["subsystems"])
            print(f"Subsystem classification seeded: {len(res['mapping'])} tables")
except Exception as e:
    print(f"Subsystem seed warning: {e}")


def schema_fingerprint(tables_data, fk_list):
    """Stable fingerprint of a schema: table/column/pk layout + FK edges."""
    lines = []
    for t in sorted(tables_data):
        d = tables_data[t]
        cols = ",".join(c["name"] for c in d.get("columns", []))
        pks = ",".join(d.get("pks") or [])
        lines.append(f"{t}:{cols}#{pks}")
    for f in sorted(fk_list, key=lambda x: (x["child"], x["parent"], x.get("cols", ""))):
        lines.append(f"{f['child']}>{f['parent']}:{f.get('cols', '')}")
    return hashlib.md5(("\n".join(lines)).encode("utf-8")).hexdigest()


def compute_subsystems(cached):
    """Compute subsystem state (definitions + mapping) for the cached schema,
    overlaying any user/AI saved definitions and table overrides."""
    res = subsys.detect_subsystems(cached["tablesData"], cached["fkList"])
    saved_defs = db.get_subsystem_defs()
    if saved_defs:
        res = subsys.detect_subsystems(
            cached["tablesData"], cached["fkList"],
            subsystem_defs=list(saved_defs.values()))
    saved_map = db.get_subsystem_mappings()
    if saved_map:
        merged = dict(res["mapping"])
        for t, k in saved_map.items():
            if t in cached["tablesData"]:
                merged[t] = k
        res = subsys.detect_subsystems(
            cached["tablesData"], cached["fkList"],
            subsystem_defs=list(saved_defs.values()) if saved_defs else None,
            custom_mapping=merged)
    return res


def classify_and_save(cached, use_ai=True):
    """Run classification (AI first, local fallback) and persist it."""
    ai_info = None
    mode = "local"
    if use_ai and ai_classify.is_ai_available():
        try:
            ai = ai_classify.classify_schema(cached["tablesData"], cached["fkList"])
            if ai:
                ai_info = ai
                mode = "ai"
        except Exception:
            ai_info = None
            mode = "local"
    defs = ai_info["subsystems"] if ai_info else None
    mapping = ai_info["mapping"] if ai_info else None
    res = subsys.detect_subsystems(
        cached["tablesData"], cached["fkList"],
        subsystem_defs=defs, custom_mapping=mapping)
    db.save_subsystem_mappings(res["mapping"])
    db.save_subsystem_defs(res["subsystems"])
    return res, mode


def ingest_schema(tables_data, fk_list, dialect, source, schema_name=None, use_ai=True):
    """Store a new/unified schema in the cache and return the enriched result."""
    fp = schema_fingerprint(tables_data, fk_list)
    old = db.get_cached_schema()
    if not old or old.get("schemaFingerprint") != fp:
        db.reset_for_new_schema()
    db.save_schema_cache(tables_data, fk_list, dialect=dialect, source=source,
                         schema_name=schema_name, fingerprint=fp)
    cached = db.get_cached_schema()
    subs, mode = classify_and_save(cached, use_ai=use_ai)
    return {
        "success": True,
        "schema": {
            "tablesData": tables_data,
            "fkList": fk_list,
            "tableCount": len(tables_data),
            "fkCount": len(fk_list),
            "dialect": dialect,
            "source": source,
            "schemaName": schema_name,
        },
        "subsystems": subs,
        "classifier": mode,
    }

app = FastAPI(title="TESTR ERD Studio Pro Server", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---
class StateSaveRequest(BaseModel):
    positions: Dict[str, Dict[str, float]]
    hidden_cols: Optional[Dict[str, List[str]]] = {}
    visible_tables: Optional[List[str]] = None
    settings: Optional[Dict[str, Any]] = None

class LayoutSaveRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    view_mode: Optional[str] = "no-audit"
    theme: Optional[str] = "mermaid"
    positions: Dict[str, Dict[str, float]]
    hidden_cols: Optional[Dict[str, List[str]]] = {}
    selected_tables: Optional[List[str]] = []

class SettingsUpdateRequest(BaseModel):
    settings: Dict[str, Any]

class DbTestRequest(BaseModel):
    user: str
    password: str
    host: Optional[str] = "localhost"
    port: Optional[int] = 1521
    service_name: Optional[str] = "orclpdb"

class DbSyncRequest(BaseModel):
    user: Optional[str] = None
    password: Optional[str] = None
    dsn: Optional[str] = None

# --- REST APIs ---

@app.get("/api/health")
def health_check():
    cached = db.get_cached_schema()
    return {
        "status": "healthy",
        "cachedTables": cached["tableCount"] if cached else 0,
        "cachedFks": cached["fkCount"] if cached else 0,
        "lastSync": cached["lastSync"] if cached else None
    }

@app.get("/api/schema")
def get_schema():
    cached = db.get_cached_schema()
    if not cached:
        res = oracle_sync.sync_schema_from_oracle()
        return res
    return {
        "success": True,
        "tablesData": cached["tablesData"],
        "fkList": cached["fkList"],
        "tableCount": cached["tableCount"],
        "fkCount": cached["fkCount"],
        "lastSync": cached["lastSync"],
        "dialect": cached.get("dialect", "oracle"),
        "source": cached.get("source", "oracle"),
        "schemaName": cached.get("schemaName"),
    }

@app.get("/api/connectors")
def list_connectors():
    return {"success": True, "connectors": db_connectors.list_connectors(), "current": {
        "dialect": (db.get_cached_schema() or {}).get("dialect", "oracle"),
        "source": (db.get_cached_schema() or {}).get("source", "oracle"),
    }}

class ConnectorRequest(BaseModel):
    dialect: str
    params: Dict[str, Any] = {}

@app.post("/api/connectors/test")
def connectors_test(req: ConnectorRequest):
    return db_connectors.test_connection(req.dialect, req.params)

@app.post("/api/connectors/connect")
def connectors_connect(req: ConnectorRequest):
    try:
        res = db_connectors.connect(req.dialect, req.params)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    schema_name = req.params.get("database") or req.params.get("service_name") or req.params.get("path")
    return ingest_schema(res["tablesData"], res["fkList"], res.get("dialect", req.dialect),
                         source=req.dialect, schema_name=schema_name, use_ai=True)

@app.post("/api/schema/import/sql")
async def import_sql(file: UploadFile = FileParam(...)):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty SQL file")
    text = content.decode("utf-8", errors="replace")
    try:
        res = sql_import.parse_sql_schema(text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ingest_schema(res["tablesData"], res["fkList"], dialect=res["dialect"],
                         source="sql", schema_name=file.filename, use_ai=True)

@app.post("/api/schema/parse")
async def parse_sql_text(payload: Dict[str, Any] = Body(...)):
    """Parse SQL DDL text WITHOUT touching the stored DB schema.

    Used by the AI assistant's "Use this code" action and by the in-app
    multi-workspace source chooser (paste / agent DDL) to draw an ER diagram
    in a new page immediately, leaving the persisted schema untouched.
    """
    text = (payload.get("sql") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty SQL text")
    try:
        res = sql_import.parse_sql_schema(text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "success": True,
        "schema": {
            "tablesData": res["tablesData"],
            "fkList": res["fkList"],
            "tableCount": len(res["tablesData"]),
            "fkCount": len(res["fkList"]),
            "dialect": res.get("dialect", "oracle"),
            "source": "agent-code",
        },
    }

@app.post("/api/dictionary/import")
async def import_data_dictionary(
    files: list[UploadFile] = FileParam(...),
    dialect: str = Form("oracle"),
    include_drop: bool = Form(True),
    store: bool = Form(True),
    audit: str = Form("keep"),
):
    """Import one or more Excel Data Dictionaries (.xlsx): one sheet per table.

    Multiple files are merged into a single schema. Converts it into DDL for
    the requested dialect (sql_export), optionally applying the audit-columns
    policy (keep / add / remove). When `store=true` replaces the loaded schema
    so the ER diagram is redrawn.
    """
    if not files:
        raise HTTPException(status_code=400, detail="لم يتم رفع أي ملف (No file uploaded)")
    tables_data: dict = {}
    raw_fks: list = []
    all_warnings: list = []
    merged_captions: dict = {}
    total_sheets = 0
    for f in files:
        data = await f.read()
        if not data:
            all_warnings.append(f"ملف «{f.filename}» فارغ وتُجاهل")
            continue
        fname = (f.filename or "").lower()
        if not fname.endswith((".xlsx", ".xlsm")):
            all_warnings.append(f"ملف «{f.filename}» ليس بصيغة Excel وتُجاهل")
            continue
        try:
            parsed = datadict_import.parse_xlsx(data)
        except Exception as e:
            all_warnings.append(f"ملف «{f.filename}»: تعذر تحليله ({e}) وتُجاهل")
            continue
        total_sheets += parsed["summary"].get("sheetCount", 0)
        for w in parsed["summary"].get("warnings", []):
            if "علاقة تشير لجداول" in w:
                continue  # re-resolved after the merge below
            all_warnings.append(f"[{f.filename}] {w}" if len(files) > 1 else w)
        for tn in parsed["tablesData"]:
            if tn in tables_data:
                all_warnings.append(f"جدول «{tn}» مكرر بين الملفات — سيبقى الأول")
                continue
            tables_data[tn] = parsed["tablesData"][tn]
        raw_fks.extend(parsed.get("rawFks") or [])
        merged_captions.update(parsed["summary"].get("captions", {}))
    if not tables_data:
        raise HTTPException(status_code=400,
                            detail="لم يُعثر على جداول صالحة في الملفات المرفوعة. تأكد من رؤوس الأعمدة (إسم الحقل / نوع البيانات / طول / PK).")
    fk_list, dangling = datadict_import._build_fk_list(raw_fks, tables_data)
    if dangling:
        all_warnings.append(f"{len(dangling)} علاقة تشير لجداول غير موجودة في الملفات وتُجاهلت (مثال: {dangling[0]})")
    if dialect not in sql_export.DIALECTS:
        dialect = "oracle"

    if audit in ("add", "remove"):
        try:
            audit_notes = datadict_import.apply_audit_policy(tables_data, audit)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"خطأ في خيار أعمدة التدقيق: {e}")
        all_warnings.extend(audit_notes)

    ddl = sql_export.generate_ddl(tables_data, fk_list, dialect=dialect,
                                  include_drop=include_drop)
    schema_meta = {
        "tablesData": tables_data,
        "fkList": fk_list,
        "tableCount": len(tables_data),
        "fkCount": len(fk_list),
        "dialect": "oracle",
        "source": "datadict",
        "schemaName": (files[0].filename if len(files) == 1 else f"{len(files)} قواميس مدموجة"),
    }
    result = {
        "success": True,
        "schema": schema_meta,
        "ddl": ddl,
        "targetDialect": dialect,
        "summary": {
            "tables": len(tables_data),
            "fks": len(fk_list),
            "warnings": all_warnings,
            "captions": merged_captions,
            "files": len(files),
            "sheetCount": total_sheets,
        },
        "audit": audit,
        "store": store,
    }
    if store:
        ing = ingest_schema(tables_data, fk_list, dialect="oracle", source="datadict",
                            schema_name=schema_meta["schemaName"], use_ai=True)
        result["subsystems"] = ing["subsystems"]
        result["classifier"] = ing["classifier"]
    return result

@app.post("/api/dictionary/export")
async def export_data_dictionary(files: list[UploadFile] = FileParam(...)):
    """Upload one or more .sql / .txt scripts and download a Data Dictionary .xlsx build.

    Multiple scripts are concatenated and parsed together as one schema.
    """
    if not files:
        raise HTTPException(status_code=400, detail="لم يتم رفع أي ملف (No file uploaded)")
    parts_text = []
    base_names = []
    for f in files:
        content = await f.read()
        if not content:
            continue
        name = (f.filename or "").lower()
        if not name.endswith((".sql", ".ddl", ".txt")):
            raise HTTPException(status_code=400,
                                detail="يدعم الملفات .sql / .ddl / .txt فقط (only SQL files are supported.)")
        parts_text.append(content.decode("utf-8", errors="replace"))
        base_names.append(re.sub(r"\.(sql|ddl|txt)$", "", name, flags=re.I) or "schema")
    if not parts_text:
        raise HTTPException(status_code=400, detail="لا يوجد محتوى صالح في الملفات المرفوعة")
    text = "\n\n".join(parts_text)
    try:
        parsed = sql_import.parse_sql_schema(text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not parsed.get("tablesData"):
        raise HTTPException(status_code=400,
                            detail="لم يُعثر على جداول في الكود المرفوع. تأكد من وجود (CREATE TABLE).")
    try:
        xlsx_bytes = datadict_export.build_workbook_bytes(parsed["tablesData"], parsed["fkList"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"تعذر توليد ملف Excel: {e}")
    base = base_names[0] if len(base_names) == 1 else "merged"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="data_dictionary_{base}.xlsx"',
            "X-Tables": str(parsed["tableCount"]),
            "X-Fks": str(parsed["fkCount"]),
        },
    )

@app.post("/api/documents/extract")
async def extract_document(file: UploadFile = FileParam(...)):
    import io as _io
    import zipfile as _zf
    import re as _re
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    name = (file.filename or "").lower()
    if name.endswith(".docx"):
        try:
            with _zf.ZipFile(_io.BytesIO(data)) as z:
                if "word/document.xml" not in z.namelist():
                    raise ValueError("word/document.xml missing")
                xml = z.read("word/document.xml").decode("utf-8", errors="replace")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"تعذر قراءة ملف DOCX (aDOCX): {e}")
        paragraphs = _re.split(r"</w:p>", xml)
        out = []
        for p in paragraphs:
            runs = _re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p)
            out.append("".join(runs).replace("&amp;", "&").replace("&lt;", "<")
                       .replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'"))
        text = "\n".join(t.strip() for t in out if t.strip())
        if not text.strip():
            raise HTTPException(status_code=400, detail="ملف DOCX لا يحتوي على نص قابل للاستخراج (aDOCX has no text.)")
        return {"success": True, "format": "docx", "text": text, "chars": len(text)}
    elif name.endswith(".doc"):
        raise HTTPException(status_code=400, detail="صيغة .doc القديمة غير مدعومة؛ حوّلها إلى .docx أو .txt (aDOC is not supported.)")
    text = data.decode("utf-8", errors="replace")
    return {"success": True, "format": "text", "text": text, "chars": len(text)}

class SchemaExportRequest(BaseModel):
    tablesData: Dict[str, Any]
    fkList: List[Dict[str, Any]] = []
    dialect: str = "mysql"
    include_drop: bool = True


@app.post("/api/schema/export")
def export_schema(req: SchemaExportRequest):
    if not req.tablesData:
        raise HTTPException(status_code=404, detail="No schema loaded")
    fks = [fk for fk in req.fkList
           if fk.get("child") in req.tablesData and fk.get("parent") in req.tablesData]
    payload = sql_export.generate_export_payload(req.tablesData, fks,
                                                 dialect=req.dialect, include_drop=req.include_drop)
    if not payload.get("success"):
        raise HTTPException(status_code=400, detail=payload.get("error", "Export failed"))
    return payload


@app.post("/api/dictionary/from-schema")
def dictionary_from_schema(req: SchemaExportRequest):
    """Build a dictionary directly from the active workspace, without SQL upload."""
    if not req.tablesData:
        raise HTTPException(status_code=400, detail="No tables in the current diagram")
    fks = [fk for fk in req.fkList
           if fk.get("child") in req.tablesData and fk.get("parent") in req.tablesData]
    try:
        content = datadict_export.build_workbook_bytes(req.tablesData, fks)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not generate dictionary: {e}")
    return Response(content=content,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": 'attachment; filename="data_dictionary.xlsx"',
                             "X-Tables": str(len(req.tablesData)), "X-Fks": str(len(fks))})

@app.post("/api/settings/test-db")
def test_oracle_connection(req: DbTestRequest):
    dsn = f"{req.host}:{req.port}/{req.service_name}"
    start_time = time.time()
    try:
        conn = oracledb.connect(user=req.user, password=req.password, dsn=dsn)
        cur = conn.cursor()
        cur.execute("SELECT banner_full FROM v$version WHERE ROWNUM=1")
        version = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM all_tables WHERE owner='{req.user.upper()}'")
        tbl_count = cur.fetchone()[0]
        conn.close()
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "success": True,
            "message": "Connection successful!",
            "latencyMs": elapsed_ms,
            "dbVersion": version,
            "tablesFound": tbl_count,
            "user": req.user,
            "dsn": dsn
        }
    except Exception as e:
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "success": False,
            "error": str(e),
            "latencyMs": elapsed_ms,
            "dsn": dsn
        }

@app.post("/api/schema/sync")
def sync_schema(req: DbSyncRequest = None):
    try:
        user = req.user if req and req.user else None
        pwd = req.password if req and req.password else None
        dsn = req.dsn if req and req.dsn else None
        res = oracle_sync.sync_schema_from_oracle(user=user, password=pwd, dsn=dsn)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/state")
def get_current_state():
    states = db.get_all_table_states()
    settings = db.get_all_settings()
    return {
        "positions": states["positions"],
        "hidden_cols": states["hidden_cols"],
        "visible_tables": states["visible_tables"],
        "settings": settings
    }

@app.post("/api/state")
def save_current_state(req: StateSaveRequest):
    try:
        db.save_all_table_states(
            positions=req.positions,
            hidden_cols=req.hidden_cols,
            visible_tables=req.visible_tables
        )
        if req.settings:
            db.update_bulk_settings(req.settings)
        return {"success": True, "message": "State auto-saved to SQLite"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/settings")
def get_settings():
    return db.get_all_settings()

@app.post("/api/settings")
def update_settings(req: SettingsUpdateRequest):
    try:
        db.update_bulk_settings(req.settings)
        return {"success": True, "settings": db.get_all_settings()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/layouts")
def list_layouts():
    return db.get_all_layouts()

@app.get("/api/layouts/{layout_id_or_name}")
def get_layout(layout_id_or_name: str):
    res = db.get_layout_by_name_or_id(layout_id_or_name)
    if not res:
        raise HTTPException(status_code=404, detail="Layout not found")
    return res

@app.post("/api/layouts")
def create_or_update_layout(req: LayoutSaveRequest):
    try:
        db.save_layout_preset(
            name=req.name,
            positions=req.positions,
            hidden_cols=req.hidden_cols or {},
            selected_tables=req.selected_tables or [],
            view_mode=req.view_mode,
            theme=req.theme,
            description=req.description
        )
        return {"success": True, "name": req.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/layouts/{layout_id_or_name}")
def delete_layout(layout_id_or_name: str):
    try:
        db.delete_layout_preset(layout_id_or_name)
        return {"success": True, "deleted": layout_id_or_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Database Backup / Restore / Factory Reset ---

@app.get("/api/db/backup")
def backup_database():
    if not os.path.exists(db.DB_PATH):
        raise HTTPException(status_code=404, detail="Database file not found")
    return FileResponse(
        db.DB_PATH,
        filename="TESTR_ERD_Studio_Backup.db",
        media_type="application/octet-stream"
    )

@app.post("/api/db/restore")
async def restore_database(file: UploadFile = FileParam(...)):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    backup_path = db.DB_PATH + ".pre_restore"
    try:
        with open(db.DB_PATH, "rb") as f:
            with open(backup_path, "wb") as bf:
                bf.write(f.read())
        with open(db.DB_PATH, "wb") as f:
            f.write(content)
        return {"success": True, "message": "Database restored. A pre-restore copy was kept as app.db.pre_restore"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/db/factory-reset")
def factory_reset():
    try:
        db.factory_reset()
        return {"success": True, "message": "Database reset to factory state"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Smart Subsystem Classification ---

@app.get("/api/subsystems")
def get_subsystems():
    cached = db.get_cached_schema()
    if not cached:
        raise HTTPException(status_code=404, detail="Schema not synced yet")
    return compute_subsystems(cached)

@app.post("/api/subsystems/save")
def save_subsystem_mapping(payload: Dict[str, Any] = Body(...)):
    mapping = payload.get("mapping") or payload.get("table_subsystem") or {}
    overrides = payload.get("overrides") or {}
    defs = payload.get("defs") or []
    all_mapping = dict(mapping)
    all_mapping.update(overrides)
    if defs:
        db.save_subsystem_defs(defs)
    if not all_mapping:
        return {"success": True, "saved": 0}
    try:
        db.save_subsystem_mappings(all_mapping)
        return {"success": True, "saved": len(all_mapping)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/subsystems/detect")
def force_detect():
    cached = db.get_cached_schema()
    if not cached:
        raise HTTPException(status_code=404, detail="Schema not synced yet")
    res, mode = classify_and_save(cached, use_ai=True)
    res["classifier"] = mode
    return res

# --- AI Assistant ---

@app.get("/api/ai/config")
def get_ai_config():
    return ai_assistant.get_ai_config()

@app.post("/api/ai/config")
def post_ai_config(payload: Dict[str, Any] = Body(...)):
    allowed = ["ai_provider", "ai_base_url", "ai_api_key", "ai_model", "ai_temperature"]
    settings = {k: str(payload[k]) for k in allowed if k in payload and payload[k] is not None}
    try:
        db.update_bulk_settings(settings)
        return {"success": True, "config": ai_assistant.get_ai_config()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/test")
def test_ai(payload: Dict[str, Any] = Body(None)):
    if payload and any(payload.get(k) is not None for k in ("ai_provider", "ai_api_key", "ai_base_url", "ai_model")):
        cfg = ai_assistant.get_ai_config()
        cfg.update({k: payload[k] for k in ("ai_provider", "ai_api_key", "ai_base_url", "ai_model") if payload.get(k) is not None})
    else:
        cfg = None
    return ai_assistant.test_provider(cfg)

@app.get("/api/ai/history")
def get_ai_history():
    return {"messages": db.get_chat_history()}

@app.delete("/api/ai/history")
def clear_ai_history():
    db.clear_chat_history()
    return {"success": True}

@app.post("/api/ai/chat")
def ai_chat(payload: Dict[str, Any] = Body(...)):
    messages = payload.get("messages") or []
    context = payload.get("context") or {}
    if not messages:
        raise HTTPException(status_code=400, detail="No messages provided")
    last = messages[-1]
    if last.get("role") != "user":
        raise HTTPException(status_code=400, detail="Last message must be from user")

    def generate():
        try:
            for ev in ai_assistant.chat_agent(messages, context):
                yield json.dumps(ev, ensure_ascii=False) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


# Mount Static Frontend
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    port = 8500
    print(f"============================================================")
    print(f"  TESTR ERD Studio Pro Server v1.1.0")
    print(f"  Running at: http://localhost:{port}")
    print(f"  SQLite Database: {db.DB_PATH}")
    print(f"============================================================")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
