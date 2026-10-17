import json
import urllib.request
import urllib.parse
import sys

BASE_URL = "http://localhost:8500"

def request_json(url, method="GET", data=None):
    headers = {"Content-Type": "application/json"} if data is not None else {}
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def test_audit_history_flow():
    print(">>> 1. Testing GET /api/audit/stats ...")
    status, res = request_json(f"{BASE_URL}/api/audit/stats")
    assert status == 200, f"Expected 200, got {status}"
    assert res.get("success") is True, f"Expected success: True, got {res}"
    print(f"Stats: {res.get('stats')}")

    print(">>> 2. Testing GET /api/audit/events ...")
    status, res = request_json(f"{BASE_URL}/api/audit/events?limit=20")
    assert status == 200
    assert res.get("success") is True
    print(f"Events count: {len(res.get('events', []))}")

    print(">>> 3. Testing POST /api/audit/snapshots (Create Snapshot) ...")
    sample_schema = {
        "tablesData": {
            "AUDIT_TEST_ORDERS": {
                "columns": [
                    {"name": "ORDER_ID", "type": "NUMBER", "pk": True, "nullable": False},
                    {"name": "CUSTOMER_ID", "type": "NUMBER", "pk": False, "nullable": False},
                    {"name": "TOTAL_AMOUNT", "type": "NUMBER(12,2)", "pk": False, "nullable": True}
                ],
                "color": "#3b82f6"
            }
        },
        "fkList": []
    }
    snap_payload = {
        "name": "Integration Test Snapshot v1.0",
        "description": "Created during automated audit history verification",
        "trigger_event": "MANUAL",
        "schema_data": sample_schema
    }
    status, res = request_json(f"{BASE_URL}/api/audit/snapshots", method="POST", data=snap_payload)
    assert status == 200
    assert res.get("success") is True
    snapshot_id = (res.get("snapshot") or {}).get("id") or res.get("snapshotId") or res.get("snapshot_id")
    assert snapshot_id, f"Missing snapshot id in response: {res}"
    print(f"Created snapshot ID: {snapshot_id}")

    print(">>> 4. Testing GET /api/audit/snapshots ...")
    status, res = request_json(f"{BASE_URL}/api/audit/snapshots")
    assert status == 200
    assert any(s["id"] == snapshot_id for s in res.get("snapshots", []))
    print(f"Total snapshots returned: {len(res.get('snapshots', []))}")

    print(f">>> 5. Testing GET /api/audit/snapshots/{snapshot_id} ...")
    status, res = request_json(f"{BASE_URL}/api/audit/snapshots/{snapshot_id}")
    assert status == 200
    assert res.get("snapshot", {}).get("name") == "Integration Test Snapshot v1.0"

    print(f">>> 6. Testing POST /api/audit/snapshots/{snapshot_id}/restore ...")
    status, res = request_json(f"{BASE_URL}/api/audit/snapshots/{snapshot_id}/restore", method="POST")
    assert status == 200
    assert res.get("success") is True
    assert "AUDIT_TEST_ORDERS" in res.get("schema", {}).get("tablesData", {})
    print("Snapshot restored successfully into active workspace cache.")

    print(">>> 7. Testing GET /api/audit/events/export?format=csv ...")
    req = urllib.request.Request(f"{BASE_URL}/api/audit/events/export?format=csv")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        raw_csv = resp.read()
        assert raw_csv.startswith(b"\xef\xbb\xbf"), "CSV missing UTF-8 BOM"
        csv_text = raw_csv.decode("utf-8")
        assert "Event ID" in csv_text and "Event Type" in csv_text
        print("CSV export verified with UTF-8 BOM header.")

    print(">>> 8. Testing GET /api/audit/events/export?format=json ...")
    req = urllib.request.Request(f"{BASE_URL}/api/audit/events/export?format=json")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        json_data = json.loads(resp.read().decode("utf-8"))
        count = len(json_data) if isinstance(json_data, list) else len(json_data.get("events", []))
        print(f"JSON export verified with {count} events.")

    print(f">>> 9. Testing DELETE /api/audit/snapshots/{snapshot_id} ...")
    status, res = request_json(f"{BASE_URL}/api/audit/snapshots/{snapshot_id}", method="DELETE")
    assert status == 200
    assert res.get("success") is True
    print("Snapshot deleted successfully.")

    print(">>> 10. Testing POST /api/audit/events/clear (Prune old logs) ...")
    status, res = request_json(f"{BASE_URL}/api/audit/events/clear", method="POST", data={"keep_latest": 50})
    assert status == 200
    assert res.get("success") is True
    print(f"Prune completed, deleted_count: {res.get('deleted_count')}")

    print("\nALL STAGE 3 AUDIT & SNAPSHOT API TESTS PASSED SUCCESSFULLY! [SUCCESS]")

if __name__ == "__main__":
    try:
        test_audit_history_flow()
    except Exception as e:
        print(f"Test failed: {e}", file=sys.stderr)
        sys.exit(1)
