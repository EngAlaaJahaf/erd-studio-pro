"""LLM-driven diagram extraction: given a section of a documentation file and a
desired diagram type, ask an OpenAI-compatible chat-completions backend for a
clean JSON diagram spec. Falls back to the local extractor when unavailable.
"""

import re

import requests

import ai_classify
from diagram_extract import extract as extract_local

_TYPE_SPEC = {
    "sequence": (
        "a UML sequence diagram. Identify the actors/participants (people and systems) "
        "and the ordered messages exchanged between them. UTF-8 Arabic labels are fine."
    ),
    "activity": (
        "a UML activity diagram: steps (actions), decisions (conditions), and the "
        "start/end markers. Keep ids unique and short (n1, n2, ...)."
    ),
    "usecase": (
        "a UML use case diagram: the actors, the use cases performed by the system, "
        "associations between actors and use cases, and optional include/extend relations."
    ),
}

_JSON_SHAPES = {
    "sequence": ('{"type":"sequence","title":"...","participants":["A","B"],'
                 '"messages":[{"from":"A","to":"B","label":"..."}],'
                 '"notes":[{"from":"A","to":"B","text":"..."}]}'),
    "activity": ('{"type":"activity","title":"...","nodes":[{"id":"n1","type":"action|decision|start|end","label":"..."}],'
                 '"edges":[{"from":"n1","to":"n2","label":"yes/no optional"}]}'),
    "usecase": ('{"type":"usecase","title":"...","system":"...",'
                '"actors":[{"id":"a1","name":"..."}],'
                '"usecases":[{"id":"u1","name":"..."}],'
                '"associations":[{"actor":"a1","usecase":"u1"}],'
                '"includes":[{"from":"u1","to":"u2"}],"extends":[]}'),
}


def config():
    return ai_classify._config()


def is_ai_available():
    cfg = config()
    return cfg["provider"] == "cloud" and bool(cfg["api_key"]) and bool(cfg["base_url"])


def _build_prompt(text, diagram_type):
    type_desc = _TYPE_SPEC.get(diagram_type, _TYPE_SPEC["sequence"])
    shape = _JSON_SHAPES.get(diagram_type, _JSON_SHAPES["sequence"])
    return (
        "You are a UML diagram analyst. The user will give you a slice of a project "
        "documentation file. Produce STRICT JSON (no markdown, no extra text) describing "
        + type_desc + "\n"
        "- Use the actual roles, steps and objects mentioned in the text; do not invent.\n"
        "- Label everything in the same language as the input (Arabic stays Arabic).\n"
        "- Keep labels short (max ~90 chars), 4-16 items total.\n"
        "Return exactly this JSON shape:\n" + shape + "\n\n"
        "DOCUMENT SECTION:\n" + text + "\n\nJSON:"
    )


def generate_with_llm(text, diagram_type):
    """Returns a diagram spec dict. Raises ValueError on failure."""
    if not is_ai_available():
        raise ValueError("no cloud AI configured")
    prompt = _build_prompt(text, diagram_type)
    cfg = config()
    url = f"{cfg['base_url']}/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {cfg['api_key']}"}
    body = {
        "model": cfg["model"],
        "temperature": 0.2,
        "messages": [
            {"role": "system",
             "content": "You extract strict JSON diagram specs from documentation. No markdown."},
            {"role": "user", "content": prompt},
        ],
    }
    resp = requests.post(url, headers=headers, json=body, timeout=120)
    if resp.status_code != 200:
        raise ValueError(f"LLM request failed: HTTP {resp.status_code}")
    content = resp.json()["choices"][0]["message"]["content"]
    spec = ai_classify._extract_json(content)
    spec["type"] = diagram_type
    return spec


def generate(text, diagram_type, prefer_llm=True):
    """Generate a diagram spec for a text section. Returns (spec, provider, warnings)."""
    warnings = []
    if prefer_llm and is_ai_available():
        try:
            spec = generate_with_llm(text, diagram_type)
            try:
                from diagram_specs import normalize_spec
                normalize_spec(spec)
                return spec, "ai", warnings
            except (ValueError, TypeError, KeyError) as e:
                warnings.append(f"LLM spec was invalid ({e}); used local extractor.")
        except Exception as e:
            warnings.append(f"LLM path failed ({e}); used local extractor.")
    spec, local_warnings = extract_local(text, diagram_type)
    warnings.extend(local_warnings)
    return spec, "local", warnings