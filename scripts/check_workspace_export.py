"""Check that SQL export uses current visible tables, independently of DB cache."""
import json
import subprocess
import sys
from io import BytesIO
from openpyxl import load_workbook
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.main import SchemaExportRequest, export_schema, dictionary_from_schema

html = (ROOT / 'static/js/app.js').read_text(encoding='utf-8')
function = html[html.index('function currentDiagramSchema('):html.index('async function exportSchema(')]
js = '''
let tablesData, selectedTables, fkList;
const payloads = [];
function fetch(url, options) {
  if (url !== '/api/schema/export' || options.method !== 'POST') throw Error('Wrong route');
  payloads.push(JSON.parse(options.body));
}
''' + function + '''
const table = {columns: [{name: 'id', type: 'INT'}], pks: ['id']};
tablesData = {users: table, apps: table, hidden: table};
selectedTables = new Set(['users', 'apps']);
fkList = [{child: 'apps', parent: 'users', cols: 'id', fk: 'fk_apps_users'},
          {child: 'apps', parent: 'hidden', cols: 'id', fk: 'fk_hidden'}];
requestCurrentSchemaExport('mysql', false);
tablesData = {students: table}; selectedTables = new Set(['students']); fkList = [];
requestCurrentSchemaExport('postgres', false);
process.stdout.write(JSON.stringify(payloads));
'''
result = subprocess.run(['node', '-'], input=js, encoding='utf-8', capture_output=True, check=True)
first, second = json.loads(result.stdout)
assert set(first['tablesData']) == {'users', 'apps'}
assert len(first['fkList']) == 1
assert set(second['tablesData']) == {'students'}
for payload, names, absent in [(first, ['users', 'apps'], ['students', 'hidden']),
                               (second, ['students'], ['users', 'apps'])]:
    exported = export_schema(SchemaExportRequest(**payload))
    assert exported['success'] and exported['tableCount'] == len(names)
    assert all(name in exported['script'] for name in names)
    assert all(name not in exported['script'] for name in absent)
    dictionary = dictionary_from_schema(SchemaExportRequest(**payload))
    assert dictionary.headers['X-Tables'] == str(len(names))
    workbook = load_workbook(BytesIO(dictionary.body), read_only=True)
    values = {str(value) for sheet in workbook for row in sheet.values for value in row if value is not None}
    assert all(name in values for name in names), values
    assert not any(name in values for name in absent)
    workbook.close()
print('PASS: two independent workspace exports, visible tables and internal FKs only')
print('PASS: direct Excel dictionaries contain only their source workspace tables')
