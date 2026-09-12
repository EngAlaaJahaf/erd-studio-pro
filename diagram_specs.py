"""Unified UML diagram specs and dual renderers: Mermaid (in-app preview) and
draw.io mxGraph XML (downloadable .drawio that opens directly in draw.io).

The whole app is text-first: a user pastes or uploads a documentation file,
picks a section (see document_sections.split_sections) and a diagram type,
and the backend builds one of these three spec shapes:

  sequence: {type, title, participants:[str], messages:[{from,to,label}],
             notes:[{from,to,text}]}
  activity: {type, title, nodes:[{id,type,label}], edges:[{from,to,label}]}
  usecase:  {type, title, system, actors:[{id,name}], usecases:[{id,name}],
             associations:[{actor,usecase}], includes/extends:[{from,to}]}

The same spec renders as Mermaid text and as draw.io XML so the user can keep
working in either tool.
"""

import datetime
import json
import re
import xml.sax.saxutils as _sax

TYPES = ["sequence", "activity", "usecase"]


def _x(text):
    """Escape text for XML attribute / node content."""
    return _sax.escape(str(text or ""), {'"': "&quot;"})


def _id(text):
    """Safe id token derived from a label."""
    s = re.sub(r"[^A-Za-z0-9_]", "_", str(text))[:24].strip("_") or "x"
    return s


def _mm_label(label):
    """Mermaid-safe single-line label (no pipes outside, no braces issues)."""
    return str(label or "").replace("\n", " ").replace("\r", "").replace('"', "'").strip()


# ---------------------------------------------------------------------------
# Spec validation / normalization
# ---------------------------------------------------------------------------
def normalize_spec(spec):
    """Coerce any loosely typed spec (e.g. from an LLM) into a clean shape."""
    if not isinstance(spec, dict):
        raise ValueError("diagram spec must be a JSON object")
    stype = str(spec.get("type") or "").strip().lower()
    if stype not in TYPES:
        raise ValueError(f"unsupported diagram type: {stype or '(missing)'}")
    spec = {k: v for k, v in spec.items()}
    spec["type"] = stype
    spec.setdefault("title", "")
    if stype == "sequence":
        participants = []
        seen = set()
        for p in spec.get("participants") or []:
            p = str(p or "").strip()
            if p and p not in seen:
                seen.add(p)
                participants.append(p)
        if not participants:
            raise ValueError("sequence diagram needs at least 2 participants")
        if len(participants) < 2:
            participants.append("النظام")
        spec["participants"] = participants
        msgs = []
        for m in spec.get("messages") or []:
            if isinstance(m, dict) and m.get("from") and m.get("to"):
                msgs.append({
                    "from": str(m["from"]).strip(),
                    "to": str(m["to"]).strip(),
                    "label": _mm_label(m.get("label")),
                })
        if not msgs:
            raise ValueError("sequence diagram needs at least 1 message")
        spec["messages"] = msgs
        notes = []
        for n in spec.get("notes") or []:
            if isinstance(n, dict) and n.get("text"):
                notes.append({
                    "from": str(n.get("from") or spec["participants"][0]).strip(),
                    "to": str(n.get("to") or spec["participants"][-1]).strip(),
                    "text": _mm_label(n.get("text")),
                })
        spec["notes"] = notes
        return spec

    if stype == "activity":
        nodes = []
        ids = set()
        labels = set()
        for n in spec.get("nodes") or []:
            if not isinstance(n, dict) or not n.get("label"):
                continue
            ntype = str(n.get("type") or "action").strip().lower()
            if ntype not in ("action", "decision", "start", "end"):
                ntype = "action"
            label = _mm_label(n.get("label"))
            if not label or label in labels:
                continue
            labels.add(label)
            nid = str(n.get("id") or "").strip() or _id(label)
            base, i = nid, 0
            while nid in ids:
                i += 1
                nid = f"{base}_{i}"
            ids.add(nid)
            nodes.append({"id": nid, "type": ntype, "label": label})
        if not nodes:
            raise ValueError("activity diagram needs at least one node")
        if not any(n["type"] == "start" for n in nodes):
            nodes.insert(0, {"id": "start", "type": "start", "label": spec.get("start_label") or "ابدأ"})
        if not any(n["type"] == "end" for n in nodes):
            nodes.append({"id": "end", "type": "end", "label": spec.get("end_label") or "نهاية"})
        valid = set(n["id"] for n in nodes)
        edges = []
        used_from = set()
        for e in spec.get("edges") or []:
            if not isinstance(e, dict):
                continue
            f, t = str(e.get("from") or "").strip(), str(e.get("to") or "").strip()
            if f not in valid or t not in valid or f == t:
                continue
            if (f, t) in used_from:
                continue
            used_from.add((f, t))
            edges.append({"from": f, "to": t, "label": _mm_label(e.get("label"))})
        spec["nodes"] = nodes
        spec["edges"] = edges
        return spec

    # usecase
    actors, usecases = [], []
    seen = set()
    for a in spec.get("actors") or []:
        if not isinstance(a, dict) or not a.get("name"):
            continue
        name = str(a["name"]).strip()
        aid = str(a.get("id") or "").strip() or _id(name)
        if aid in seen or not name:
            continue
        seen.add(aid)
        actors.append({"id": aid, "name": name})
    seen = set()
    for u in spec.get("usecases") or []:
        if not isinstance(u, dict) or not u.get("name"):
            continue
        name = str(u["name"]).strip()
        uid = str(u.get("id") or "").strip() or _id(name)
        if uid in seen or not name:
            continue
        seen.add(uid)
        usecases.append({"id": uid, "name": name})
    if not actors or not usecases:
        raise ValueError("use case diagram needs at least one actor and one use case")
    av = set(a["id"] for a in actors)
    uv = set(u["id"] for u in usecases)
    assoc = []
    for a in spec.get("associations") or []:
        if isinstance(a, dict) and a.get("actor") in av and a.get("usecase") in uv:
            assoc.append({"actor": str(a["actor"]), "usecase": str(a["usecase"])})
    if not assoc:
        # default: tie actors to the first use case, then drain remaining
        for i, u in enumerate(usecases):
            actor = actors[i % len(actors)]
            assoc.append({"actor": actor["id"], "usecase": u["id"]})
    spec["actors"] = actors
    spec["usecases"] = usecases
    spec["associations"] = assoc
    for key in ("includes", "extends", "generalizations"):
        out = []
        for e in spec.get(key) or []:
            if isinstance(e, dict) and e.get("from") in uv and e.get("to") in uv and e["from"] != e["to"]:
                out.append({"from": str(e["from"]), "to": str(e["to"])})
        spec[key] = out
    return spec


# ---------------------------------------------------------------------------
# Mermaid rendering
# ---------------------------------------------------------------------------
_MM_RESERVED = {"sequence", "actor", "activate", "deactivate", "par", "loop",
                "alt", "opt", "and", "end", "note", "participant"}


def _participant_ids(participants):
    """Unique, Mermaid-safe ids keyed by participant label."""
    ids, used = {}, set()
    for i, p in enumerate(participants, 1):
        base = f"s{i}"
        while base.lower() in used:
            base += "x"
        used.add(base.lower())
        ids[p] = base
    return ids


def to_mermaid(spec):
    spec = normalize_spec(spec)
    t = spec["type"]
    title = f'---\ntitle: {_mm_label(spec.get("title") or t)}\n---\n' if spec.get("title") else ""
    if t == "sequence":
        ids = _participant_ids(spec["participants"])
        lines = ["sequenceDiagram"]
        for p in spec["participants"]:
            alias = _mm_label(p)
            if not re.fullmatch(r"[A-Za-z0-9 _\-()]+", alias):
                alias = '"' + alias.replace('"', "'") + '"'
            lines.append(f"    participant {ids[p]} as {alias}")
        for n in spec.get("notes") or []:
            fr = ids.get(n["from"], next(iter(ids.values())))
            to = ids.get(n["to"], next(iter(ids.values())))
            lines.append(f"    Note over {fr},{to}: {n['text']}")
        for m in spec["messages"]:
            fr = ids.get(m["from"], next(iter(ids.values())))
            to = ids.get(m["to"], next(iter(ids.values())))
            lines.append(f"    {fr}->>{to}: {m['label']}")
        return title + "\n".join(lines)

    if t == "activity":
        lines = ["flowchart TD"]
        for n in spec["nodes"]:
            lbl = _mm_label(n["label"])
            nid = "s0" if n["type"] == "start" else n["id"]
            nid = "e0" if n["type"] == "end" else nid
            if n["type"] == "start":
                lines.append(f'    {nid}(["{lbl}"])')
            elif n["type"] == "end":
                lines.append(f'    {nid}(["{lbl}"])')
            elif n["type"] == "decision":
                lines.append('    ' + nid + '{' + '"' + lbl + '"' + '}')
            else:
                lines.append(f'    {nid}["{lbl}"]')
        for e in spec["edges"]:
            lbl = _mm_label(e.get("label"))
            fr = "s0" if e["from"] == "start" else e["from"]
            fr = "e0" if fr == "end" else fr
            to = "e0" if e["to"] == "end" else e["to"]
            to = "s0" if to == "start" else to
            if lbl:
                lines.append(f'    {fr} -- "{lbl}" --> {to}')
            else:
                lines.append(f'    {fr} --> {to}')
        return title + "\n".join(lines)

    # usecase
    lines = ["flowchart TD"]
    for a in spec["actors"]:
        lines.append(f'    {a["id"]}["{_mm_label(a["name"])}"]')
    sysname = _mm_label(spec.get("system") or "نظام")
    lines.append(f'    subgraph SYSTEM["{sysname}"]')
    for u in spec["usecases"]:
        lines.append(f'      {u["id"]}(("{_mm_label(u["name"])}"))')
    lines.append("    end")
    for a in spec["associations"]:
        lines.append(f'    {a["actor"]} --> {a["usecase"]}')
    for e in spec.get("includes") or []:
        lines.append(f'    {e["from"]} -. include .-> {e["to"]}')
    for e in spec.get("extends") or []:
        lines.append(f'    {e["from"]} -. extend .-> {e["to"]}')
    for e in spec.get("generalizations") or []:
        lines.append(f'    {e["from"]} -. generalization .-> {e["to"]}')
    return title + "\n".join(lines)


# ---------------------------------------------------------------------------
# draw.io mxGraph XML rendering
# ---------------------------------------------------------------------------
def _mx_header(name):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace(":", "")
    return (
        '<mxfile host="TESTR-ERD-Studio" modified="{now}" agent="TESTR ERD Studio Pro" '
        'version="16.0.0" type="device">\n'
        '<diagram id="{diag}" name="{name}">\n'
        '<mxGraphModel dx="1000" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" '
        'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1400" '
        'pageHeight="1000" math="0" shadow="0">\n'
        '  <root>\n'
        '    <mxCell id="0"/>\n'
        '    <mxCell id="1" parent="0"/>\n'
        .format(now=_x(now), diag="d_" + re.sub(r"\W", "", name)[:20] or "d0", name=_x(name))
    )


def _mx_vertex(cid, value, style, x, y, w, h, parent="1"):
    return (f'    <mxCell id="{cid}" value="{_x(value)}" style="{_x(style)}" '
            f'vertex="1" parent="{parent}">\n'
            f'      <mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>\n'
            f'    </mxCell>\n')


def _mx_edge(cid, value, style, source, target, parent="1"):
    return (f'    <mxCell id="{cid}" value="{_x(value)}" style="{_x(style)}" '
            f'edge="1" parent="{parent}" source="{source}" target="{target}">\n'
            f'      <mxGeometry relative="1" as="geometry"/>\n'
            f'    </mxCell>\n')


def _mx_footer():
    return "  </root>\n</mxGraphModel>\n</diagram>\n</mxfile>\n"


def to_drawio(spec, name="diagram"):
    spec = normalize_spec(spec)
    t = spec["type"]
    cells = []
    counter = [0]

    def vid(prefix):
        counter[0] += 1
        return f"{prefix}{counter[0]}"

    name = str(name or (spec.get("title") or t))
    if t == "sequence":
        PAD, W, H_TOPBAR, LIFELINE_H, MSG_GAP = 60, 130, 34, 360, 46
        n = len(spec["participants"])
        width = W * n + PAD * (n + 1) + 40
        bar_y = 60
        cxs = []
        for i, p in enumerate(spec["participants"]):
            cid = vid("p")
            cxs.append(PAD + i * (W + PAD) + W / 2)
            style = "rounded=0;whiteSpace=wrap;html=1;fontSize=12;strokeColor=#1f2937;fillColor=#dbeafe;verticalAlign=middle;"
            cells.append(_mx_vertex(cid, p, style, PAD + i * (W + PAD), bar_y, W, H_TOPBAR))
            life_id = vid("l")
            style = "rounded=0;whiteSpace=wrap;html=1;dashed=1;fillColor=none;strokeColor=#9ca3af;verticalAlign=middle;align=center;"
            cells.append(_mx_vertex(life_id, "", style, PAD + i * (W + PAD), bar_y + H_TOPBAR, W, LIFELINE_H))
        msg_y = bar_y + H_TOPBAR + 40
        from_ix = {p: i for i, p in enumerate(spec["participants"])}
        for j, m in enumerate(spec["messages"]):
            f, tgt = from_ix.get(m["from"]), from_ix.get(m["to"])
            if f is None or tgt is None:
                continue
            cid = vid("m")
            style = "edgeStyle=orthogonalEdgeStyle;html=1;endArrow=block;rounded=0;jumpSize=6;fontSize=11;exitX=0.5;exitY=0;entryX=0.5;entryY=0;"
            cells.append(_mx_edge(cid, m["label"], style, f"p{f + 1}", f"p{tgt + 1}"))
            msg_y += MSG_GAP
        return _mx_header(name) + "".join(cells) + _mx_footer()

    if t == "activity":
        nodes = spec["nodes"]
        rows, cols = 1, len(nodes)
        # single-row flow with optional brackets
        W, H, GX, GY = 160, 54, 30, 60
        cid_map = {}
        curves = 0
        for k, n in enumerate(nodes):
            cid = vid("a")
            cid_map[n["id"]] = cid
            x, y = 50 + k * (W + GX), 80
            if n["type"] in ("start", "end"):
                style = "ellipse;whiteSpace=wrap;html=1;fillColor=#d1fae5;strokeColor=#065f46;fontSize=11;"
            elif n["type"] == "decision":
                style = "rhombus;whiteSpace=wrap;html=1;fillColor=#fef3c7;strokeColor=#92400e;fontSize=11;"
            else:
                style = "rounded=0;whiteSpace=wrap;html=1;fillColor=#dbeafe;strokeColor=#1e3a8a;fontSize=11;"
            cells.append(_mx_vertex(cid, n["label"], style, x, y, W, H))
        for e in spec["edges"]:
            cid = vid("e")
            style = "edgeStyle=orthogonalEdgeStyle;html=1;endArrow=block;rounded=0;fontSize=11;"
            cells.append(_mx_edge(cid, e.get("label", ""), style, cid_map[e["from"]], cid_map[e["to"]]))
        return _mx_header(name) + "".join(cells) + _mx_footer()

    # usecase
    A_W, UC_W, UC_H = 90, 180, 44
    actors = spec["actors"]
    usecases = spec["usecases"]
    a_x, a_y = 40, 200
    ac_y = 200
    sys_x, sys_w = a_x + A_W + 60, max(UC_W + 80, len(usecases) * (UC_W + 24) + 60)
    sys_h = 60 + len(usecases) * (UC_H + 30) + 30
    a_ids, u_ids = {}, {}
    for i, a in enumerate(actors):
        cid = vid("at")
        a_ids[a["id"]] = cid
        style = "shape=mxgraph.uml2.actor;verticalLabelPosition=bottom;html=1;whiteSpace=wrap;fontSize=12;"
        cells.append(_mx_vertex(cid, a["name"], style, a_x, ac_y + i * 90, A_W, A_W))
    sys_id = vid("sys")
    style = "rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#374151;fontSize=12;verticalAlign=top;align=left;spacingLeft=12;spacingTop=8;"
    cells.append(_mx_vertex(sys_id, spec.get("system") or "نظام", style, sys_x, 40, sys_w, sys_h))
    for i, u in enumerate(usecases):
        cid = vid("uc")
        u_ids[u["id"]] = cid
        x = sys_x + 30 + (i % 2) * 140
        y = 70 + (i // 2) * (UC_H + 30)
        style = "ellipse;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#1f2937;fontSize=11;"
        cells.append(_mx_vertex(cid, u["name"], style, x, y, UC_W, UC_H))
    for a in spec["associations"]:
        cid = vid("e")
        style = "edgeStyle=orthogonalEdgeStyle;html=1;endArrow=open;fontSize=11;"
        cells.append(_mx_edge(cid, "", style, a_ids[a["actor"]], u_ids[a["usecase"]]))
    for key, arrow in (("includes", "include"), ("extends", "extend"), ("generalizations", "generalization")):
        for e in spec.get(key) or []:
            cid = vid("e")
            style = ("edgeStyle=orthogonalEdgeStyle;html=1;endArrow=diamond;dashed=1;fontSize=10;"
                     + ("dashed=1;" if key != "generalizations" else ""))
            cells.append(_mx_edge(cid, arrow, style, u_ids[e["from"]], u_ids[e["to"]]))
    return _mx_header(name) + "".join(cells) + _mx_footer()


def payload(spec, name="diagram"):
    """Endpoint payload: mermaid text + drawio XML + normalized spec."""
    spec = normalize_spec(spec)
    return {
        "success": True,
        "type": spec["type"],
        "title": spec.get("title") or "",
        "spec": spec,
        "mermaid": to_mermaid(spec),
        "drawio": to_drawio(spec, name=name),
        "sizeBytes": len(to_drawio(spec, name=name).encode("utf-8")),
    }


def load_spec_from_json(text):
    return json.loads(text)