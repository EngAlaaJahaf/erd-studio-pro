"""Regression check: Markdown rendering must preserve commented, multiline DDL."""
import json
import subprocess
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


class CodeReader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.blocks = []
        self.in_code = False
        self.in_pre = False

    def handle_starttag(self, tag, attrs):
        if tag == 'pre':
            self.in_pre = True
        if tag == 'code' and self.in_pre:
            self.in_code = True
            self.blocks.append('')
        elif self.in_code:
            raise AssertionError(f'Unexpected formatting tag inside SQL: {tag}')

    def handle_endtag(self, tag):
        if tag == 'pre':
            self.in_pre = False
        if tag == 'code':
            self.in_code = False

    def handle_data(self, data):
        if self.in_code:
            self.blocks[-1] += data


def check(markdown, expected):
    html = (Path(__file__).resolve().parents[1] / 'static/js/app.js').read_text(encoding='utf-8')
    source = html[html.index('function _escapeHtml('):html.index('// Delegated handler')]
    js = 'var window={__codeBlocks:[]},i18n={en:{}},currentLang="en";\n' + source
    js += '\nprocess.stdout.write(mdToHtml(' + json.dumps(markdown) + '));'
    result = subprocess.run(['node', '-'], input=js, encoding='utf-8', capture_output=True, check=True)
    reader = CodeReader()
    reader.feed(result.stdout)
    assert reader.blocks == expected, 'SQL changed during Markdown rendering'
    return reader.blocks


if __name__ == '__main__':
    ddl = '\n\n\n'.join(
        f'-- {i}. Table\nCREATE TABLE t{i} (\n id BIGINT PRIMARY KEY,\n name VARCHAR(50)\n);'
        for i in range(1, 11)
    )
    indexes = '-- Index\nCREATE INDEX idx_name ON t1(name);'
    check('## DDL\n\n```sql\n' + ddl + '\n```\n\n## Indexes\n\n```sql\n' + indexes + '\n```', [ddl, indexes])
    print('PASS: ten commented tables and a separate index block preserved exactly')
    if '--history' in sys.argv:
        import requests
        base = 'http://127.0.0.1:8600'
        messages = requests.get(base + '/api/ai/history', timeout=15).json()['messages']
        originals = [m['content'] for m in messages if m.get('role') == 'assistant'
                     and 'CREATE TABLE users' in m.get('content', '')
                     and 'CREATE TABLE orders' in m.get('content', '')]
        assert originals, 'Original response not found'
        text = originals[-1]
        expected = [re.sub(r'\n$', '', m.group(2))
                    for m in re.finditer(r'```(\w*)\n?([\s\S]*?)```', text)]
        blocks = check(text, expected)
        response = requests.post(base + '/api/schema/parse',
                                 json={'sql': '\n\n'.join(blocks)}, timeout=30)
        response.raise_for_status()
        tables = response.json()['schema']['tablesData']
        assert len(tables) == 10, list(tables)
        print('PASS: original response imports all ten tables:', ', '.join(tables))
