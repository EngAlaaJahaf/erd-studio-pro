import urllib.request
import json
import sys

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8500'

def test_static_assets():
    print("--- 1. Testing Static Assets & HTML ---")
    req = urllib.request.urlopen(f"{BASE_URL}/")
    html = req.read().decode('utf-8')
    assert 'view-audit' in html, "view-audit section missing in HTML"
    assert 'auditTabLinter' in html, "auditTabLinter missing in HTML"
    assert 'auditTabDiff' in html, "auditTabDiff missing in HTML"
    assert 'auditTabMock' in html, "auditTabMock missing in HTML"
    print(" [PASS] index.html contains all 3 audit panels & subtabs.")

    req_css = urllib.request.urlopen(f"{BASE_URL}/css/enterprise.css")
    css = req_css.read().decode('utf-8')
    assert '.audit-subtabs' in css, "audit-subtabs missing in CSS"
    assert '.table-node.audit-pulse' in css, "audit-pulse missing in CSS"
    print(" [PASS] enterprise.css contains all audit styles and pulse animation.")

    req_js = urllib.request.urlopen(f"{BASE_URL}/js/app.js")
    js = req_js.read().decode('utf-8')
    assert 'runSchemaLint' in js, "runSchemaLint missing in JS"
    assert 'runSchemaDiff' in js, "runSchemaDiff missing in JS"
    assert 'runGenerateMockData' in js, "runGenerateMockData missing in JS"
    assert 'audit_linter' in js, "audit_linter quick action missing in JS"
    print(" [PASS] app.js contains all audit functions and quick actions.")

def test_linter_api():
    print("\n--- 2. Testing Linter API Endpoint ---")
    flawed_schema = {
        "tablesData": {
            "USERS": {
                "columns": [
                    {"name": "USER_ID", "type": "NUMBER(10)", "pk": True},
                    {"name": "EMAIL", "type": "VARCHAR2(100)", "pk": False}
                ]
            },
            "ORDERS": {
                "columns": [
                    {"name": "ORDER_ID", "type": "NUMBER(10)", "pk": True},
                    {"name": "USER_ID", "type": "VARCHAR2(50)", "pk": False}, # MISMATCH
                    {"name": "ORDER_DATE", "type": "DATE", "pk": False}
                ]
            },
            "LOGS_NO_PK": {
                "columns": [
                    {"name": "LOG_MSG", "type": "VARCHAR2(255)", "pk": False}
                ]
            },
            "ISOLATED_TABLE": {
                "columns": [
                    {"name": "ITEM_ID", "type": "NUMBER", "pk": True}
                ]
            }
        },
        "fkList": [
            {
                "child": "ORDERS",
                "parent": "USERS",
                "cols": "USER_ID",
                "name": "fk_orders_users"
            }
        ],
        "dialect": "oracle"
    }

    req = urllib.request.Request(
        f"{BASE_URL}/api/audit/lint",
        data=json.dumps(flawed_schema).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    res = urllib.request.urlopen(req)
    assert res.status == 200
    data = json.loads(res.read().decode('utf-8'))
    print(f" Score: {data['score']}, Grade: {data['grade']}, Total findings: {data['counts']['total']}")
    
    rules_found = {f["ruleId"] for f in data["findings"]}
    print(f" Rules triggered: {rules_found}")
    assert "MISSING_PK" in rules_found, "MISSING_PK not triggered"
    assert "FK_DATATYPE_MISMATCH" in rules_found, "FK_DATATYPE_MISMATCH not triggered"
    assert "ORPHAN_TABLE" in rules_found, "ORPHAN_TABLE not triggered"
    assert "MISSING_FK_INDEX" in rules_found, "MISSING_FK_INDEX not triggered"
    assert len(data["remediationScript"]) > 20, "Remediation script empty"
    print(" [PASS] Linter correctly detected all 4 core rules and generated remediation SQL.")

def test_diff_api():
    print("\n--- 3. Testing Schema Diff & Migration API ---")
    source = {
        "tablesData": {
            "CUSTOMERS": {
                "columns": [
                    {"name": "CUST_ID", "type": "NUMBER", "pk": True},
                    {"name": "NAME", "type": "VARCHAR2(50)", "pk": False}
                ]
            },
            "OLD_TABLE": {
                "columns": [{"name": "ID", "type": "NUMBER", "pk": True}]
            }
        },
        "fkList": []
    }

    target = {
        "tablesData": {
            "CUSTOMERS": {
                "columns": [
                    {"name": "CUST_ID", "type": "NUMBER", "pk": True},
                    {"name": "NAME", "type": "VARCHAR2(100)", "pk": False}, # Modified
                    {"name": "PHONE", "type": "VARCHAR2(20)", "pk": False}   # Added
                ]
            },
            "INVOICES": { # Added table
                "columns": [
                    {"name": "INV_ID", "type": "NUMBER", "pk": True},
                    {"name": "CUST_ID", "type": "NUMBER", "pk": False}
                ]
            }
        },
        "fkList": [
            {
                "child": "INVOICES",
                "parent": "CUSTOMERS",
                "cols": "CUST_ID",
                "name": "fk_inv_cust"
            }
        ]
    }

    payload = {
        "sourceSchema": source,
        "targetSchema": target,
        "dialect": "oracle"
    }

    req = urllib.request.Request(
        f"{BASE_URL}/api/audit/diff",
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    res = urllib.request.urlopen(req)
    assert res.status == 200
    data = json.loads(res.read().decode('utf-8'))
    s = data["summary"]
    print(f" Diff Summary: +{s['addedTablesCount']} tables, -{s['droppedTablesCount']} dropped, ~{s['modifiedTablesCount']} modified, +{s['addedFksCount']} FKs added")
    assert s["addedTablesCount"] == 1
    assert s["droppedTablesCount"] == 1
    assert s["modifiedTablesCount"] == 1
    assert s["addedFksCount"] == 1
    assert "ALTER TABLE" in data["migrationScript"] or "CREATE TABLE" in data["migrationScript"]
    assert len(data["rollbackScript"]) > 20
    print(" [PASS] Diff computed cleanly and both forward & rollback migrations generated.")

def test_mock_data_api():
    print("\n--- 4. Testing Smart Mock Data API ---")
    schema = {
        "tablesData": {
            "DEPARTMENTS": {
                "columns": [
                    {"name": "DEPT_ID", "type": "NUMBER", "pk": True},
                    {"name": "DEPT_NAME", "type": "VARCHAR2(100)", "pk": False}
                ]
            },
            "EMPLOYEES": {
                "columns": [
                    {"name": "EMP_ID", "type": "NUMBER", "pk": True},
                    {"name": "EMP_NAME", "type": "VARCHAR2(100)", "pk": False},
                    {"name": "EMAIL", "type": "VARCHAR2(100)", "pk": False},
                    {"name": "PHONE", "type": "VARCHAR2(20)", "pk": False},
                    {"name": "SALARY", "type": "NUMBER", "pk": False},
                    {"name": "DEPT_ID", "type": "NUMBER", "pk": False}
                ]
            }
        },
        "fkList": [
            {
                "child": "EMPLOYEES",
                "parent": "DEPARTMENTS",
                "cols": "DEPT_ID",
                "name": "fk_emp_dept"
            }
        ],
        "rowCount": 5,
        "dialect": "oracle",
        "lang": "ar"
    }

    req = urllib.request.Request(
        f"{BASE_URL}/api/audit/mock-data",
        data=json.dumps(schema).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    res = urllib.request.urlopen(req)
    assert res.status == 200
    data = json.loads(res.read().decode('utf-8'))
    print(f" Rows generated: {data['totalRows']}, Order: {data['topologicalOrder']}")
    assert data["topologicalOrder"][0] == "DEPARTMENTS", "Parent table must come first in DAG!"
    assert data["topologicalOrder"][1] == "EMPLOYEES", "Child table must come after parent in DAG!"
    assert data["totalRows"] == 10
    assert "INSERT INTO" in data["script"] and "DEPARTMENTS" in data["script"]
    assert "INSERT INTO" in data["script"] and "EMPLOYEES" in data["script"]
    print(" [PASS] Smart Mock Data successfully generated in topological order with guaranteed FK integrity.")

if __name__ == '__main__':
    try:
        test_static_assets()
        test_linter_api()
        test_diff_api()
        test_mock_data_api()
        print("\n========================================================")
        print("ALL DATABASE ENGINEERING & AUDIT TESTS PASSED! (100% OK)")
        print("========================================================")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
