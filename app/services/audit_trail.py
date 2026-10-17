"""Enterprise Audit Trail & Historical Versioning Service.
Provides enterprise logging, searchable audit trails, schema snapshot versioning (time machine),
and seamless rollback/restore capabilities.
"""

import json
import csv
import io
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from app.core import database as db

# Event Type Constants
EVENT_LINT_AUDIT = "LINT_AUDIT"
EVENT_QUICK_FIX = "QUICK_FIX"
EVENT_MIGRATION_DRY_RUN = "MIGRATION_DRY_RUN"
EVENT_MIGRATION_LIVE = "MIGRATION_LIVE"
EVENT_SCHEMA_SNAPSHOT = "SCHEMA_SNAPSHOT"
EVENT_SCHEMA_RESTORE = "SCHEMA_RESTORE"
EVENT_SCHEMA_SYNC = "SCHEMA_SYNC"
EVENT_MOCK_DATA = "MOCK_DATA"


def log_event(
    event_type: str,
    title: str,
    description: Optional[str] = None,
    severity: str = "INFO",
    actor: str = "SYSTEM",
    dialect: Optional[str] = None,
    target_db: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    snapshot_id: Optional[int] = None
) -> int:
    """Record an enterprise audit event into SQLite audit log."""
    return db.record_audit_event(
        event_type=event_type,
        title=title,
        description=description,
        severity=severity,
        actor=actor,
        dialect=dialect,
        target_db=target_db,
        details=details,
        snapshot_id=snapshot_id
    )


def take_snapshot(
    name: str,
    trigger_event: str = "MANUAL",
    description: Optional[str] = None,
    actor: str = "USER",
    tables_data: Optional[Dict[str, Any]] = None,
    fk_list: Optional[List[Dict[str, Any]]] = None,
    dialect: Optional[str] = None
) -> Dict[str, Any]:
    """Capture a historical schema snapshot and log an audit event."""
    if not tables_data:
        cached = db.get_cached_schema() or {}
        tables_data = cached.get("tablesData") or {}
        fk_list = cached.get("fkList") or []
        dialect = dialect or cached.get("dialect", "oracle")
        source = cached.get("source", "canvas")
        fp = cached.get("schemaFingerprint", "")
    else:
        cached = db.get_cached_schema() or {}
        source = cached.get("source", "canvas")
        fp = ""

    if not tables_data:
        raise ValueError("المخطط فارغ ولا يمكن إنشاء لقطة تاريخية لمخطط خالي من الجداول.")

    snap_id = db.create_schema_snapshot(
        name=name,
        tables_data=tables_data,
        fk_list=fk_list or [],
        trigger_event=trigger_event,
        description=description,
        dialect=dialect or "oracle",
        source=source,
        fingerprint=fp
    )

    # Log the audit event linked to this snapshot
    event_id = log_event(
        event_type=EVENT_SCHEMA_SNAPSHOT,
        title=f"أخذ لقطة للمخطط: {name}",
        description=description or f"حفظ لقطة للمخطط تحتوي على {len(tables_data)} جدول و {len(fk_list or [])} علاقة.",
        severity="INFO",
        actor=actor,
        dialect=dialect,
        details={
            "snapshotId": snap_id,
            "triggerEvent": trigger_event,
            "tableCount": len(tables_data),
            "fkCount": len(fk_list or [])
        },
        snapshot_id=snap_id
    )

    snap_obj = db.get_schema_snapshot_by_id(snap_id)
    return {
        "success": True,
        "snapshotId": snap_id,
        "snapshot_id": snap_id,
        "snapshot": snap_obj,
        "eventId": event_id,
        "name": name,
        "tableCount": len(tables_data),
        "fkCount": len(fk_list or []),
        "createdAt": datetime.now().isoformat()
    }


def restore_snapshot(snapshot_id: int, actor: str = "USER") -> Dict[str, Any]:
    """Restore active schema from a historical snapshot."""
    snap = db.get_schema_snapshot_by_id(snapshot_id)
    if not snap:
        raise ValueError(f"لم يتم العثور على لقطة المخطط بالمعرف #{snapshot_id}")

    tables_data = snap.get("tablesData") or {}
    fk_list = snap.get("fkList") or []
    dialect = snap.get("dialect", "oracle")
    source = f"snapshot:#{snapshot_id}"
    schema_name = snap.get("snapshot_name")

    # Ingest restored schema into cache and recalculate subsystems
    from app.main import ingest_schema
    res = ingest_schema(tables_data, fk_list, dialect, source, schema_name=schema_name)

    # Log the restore event
    log_event(
        event_type=EVENT_SCHEMA_RESTORE,
        title=f"استعادة المخطط من اللقطة: {schema_name}",
        description=f"تمت استعادة المخطط النشط بنجاح إلى الإصدار #{snapshot_id} المأخوذ بتاريخ {snap.get('created_at')}.",
        severity="SUCCESS",
        actor=actor,
        dialect=dialect,
        details={
            "restoredSnapshotId": snapshot_id,
            "snapshotName": schema_name,
            "tableCount": len(tables_data),
            "fkCount": len(fk_list)
        },
        snapshot_id=snapshot_id
    )

    return {
        "success": True,
        "snapshotId": snapshot_id,
        "name": schema_name,
        "tableCount": len(tables_data),
        "fkCount": len(fk_list),
        "schema": res.get("schema")
    }


def export_audit_log_csv(events: List[Dict[str, Any]]) -> str:
    """Generate RFC 4180 compliant CSV export of audit log events."""
    output = io.StringIO()
    # Write UTF-8 BOM so Excel opens Arabic correctly
    output.write('\ufeff')
    writer = csv.writer(output)
    writer.writerow([
        "Event ID", "Timestamp", "Event Type", "Severity", "Title", "Description",
        "Actor", "Dialect", "Target DB", "Snapshot ID", "Details JSON"
    ])
    for e in events:
        writer.writerow([
            e.get("id"),
            e.get("created_at"),
            e.get("event_type"),
            e.get("severity"),
            e.get("title"),
            e.get("description") or "",
            e.get("actor"),
            e.get("dialect") or "",
            e.get("target_db") or "",
            e.get("snapshot_id") or "",
            json.dumps(e.get("details", {}), ensure_ascii=False)
        ])
    return output.getvalue()


def export_audit_log_json(events: List[Dict[str, Any]]) -> str:
    """Generate pretty JSON export of audit events."""
    return json.dumps(events, indent=2, ensure_ascii=False)
