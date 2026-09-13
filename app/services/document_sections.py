"""Turn a free-text document (pasted or uploaded .txt/.md) into selectable
sections so the user can choose exactly which part should become a diagram.

Heading detection heuristics (any of these is a section boundary):
  - Markdown headings: '#', '##', ... up to 6
  - Numbered headings: "1.", "1.1)", "١-" "2-", "1) " etc.
  - ALL-CAPS short lines (English docs)
  - Short Arabic lines ending without a sentence period and < 60 chars
  - Bullet leaders: '- ', '* ' only when the NEXT line is blank (list titles)
"""

import re

_HEADING_RE = re.compile(
    r"^\s*(?:(#{1,6})\s+|(\d+(?:\.\d+)*)[\)\.\-:]?\s+|([0-9\u0660-\u0669]+)[\-\)]\s*|-\s*)"
)

_AR_ALL_CAPS_RE = re.compile(r"^\s*([\u0600-\u06FF\s]{0,70})$")


def _looks_like_title(line):
    s = line.strip()
    if not s or len(s) > 80:
        return False
    m = _HEADING_RE.match(s)
    if m:
        body = _HEADING_RE.sub("", s, count=1).strip()
        return bool(body) and len(body) <= 70
    # ALL-CAPS starts → English title
    if s.isupper() and len(s) >= 5 and any(ch.isalpha() for ch in s):
        return True
    # short Arabic line that is not a full sentence (no trailing dot) and not
    # a bullets list item with trailing comma
    if _AR_ALL_CAPS_RE.match(s) and not s.endswith((".", "،", ",")):
        return not s.endswith(":")
    return False


def split_sections(text, min_chars=8, max_sections=40):
    """Return [{"index":0, "title":..., "content":...}, ...]."""
    raw_lines = (text or "").splitlines()
    lines, heading_ix = [], []
    for i, ln in enumerate(raw_lines):
        stripped = ln.strip()
        if not stripped or re.match(r"^\s*$", ln):
            continue
        if _looks_like_title(ln):
            heading_ix.append((len(lines), stripped))
        lines.append(stripped)

    if not lines:
        return []

    boundaries = [i for i, _ in heading_ix]
    boundaries = [i for i in boundaries if i != 0]
    if not boundaries:
        whole = "\n".join(lines)
        return [{"index": 0, "title": "المستند كاملاً (الكل)" if _has_arabic(text) else "Entire document (All)",
                 "content": whole}] if len(whole) >= min_chars else []

    sections = []
    prev = 0
    prev_title = "المستند كاملاً (الكل)" if _has_arabic(text) else "Entire document (All)"
    markers = dict(heading_ix)
    for k, b in enumerate(boundaries + [len(lines)]):
        content = "\n".join(lines[prev:b]).strip()
        if content and len(content) >= min_chars:
            sections.append({"index": k, "title": markers.get(prev, prev_title), "content": content})
        prev = b
        prev_title = markers.get(b, prev_title)
    # Prepend the pre-first-heading intro as section 0 when meaningful
    # (only if the document has an actual preamble BEFORE its first title)
    first_head = heading_ix[0][0] if heading_ix else len(lines)
    if boundaries and first_head == 0:
        intro = ""
    else:
        intro = "\n".join(lines[:first_head]).strip()
    if intro and len(intro) >= min_chars:
        t = "مقدمة" if _has_arabic(text) else "Introduction"
        if sections and sections[0]["content"] == intro:
            sections.pop(0)
        sections.insert(0, {"index": 0, "title": t, "content": intro})
    result, seen_ix = [], set()
    for s in sections:
        if s["index"] in seen_ix:
            s = dict(s)
            s["index"] = max(seen_ix) + 1 if seen_ix else 0
        seen_ix.add(s["index"])
        result.append(s)
    # collapse the redundant "intro == following document title" duplicate
    if len(result) >= 2 and result[0]["content"] == result[1]["title"]:
        result.pop(0)
        for i, s in enumerate(result):
            s["index"] = i
    return result[:max_sections]


def find_section(sections, key):
    """Resolve a user-supplied section key (index or title substring)."""
    if not key:
        return sections[0] if sections else None
    key = str(key).strip()
    if key.isdigit():
        ix = int(key)
        for s in sections:
            if s["index"] == ix:
                return s
    k = key.lower()
    for s in sections:
        if k in str(s["title"]).lower():
            return s
    return sections[0] if sections else None


def _has_arabic(text):
    return bool(re.search(r"[\u0600-\u06FF]", text or ""))