"""LLM-driven schema classification: one-shot analysis of a whole database.

Given an optional OpenAI-compatible provider + API key, asks the model to
propose a custom set of subsystems and assign every table to one of them.
This adapts to ANY database without any hard-coded taxonomy.

If anything fails (no key, network, bad JSON) the caller must fall back to
the local generic classifier (subsystems.detect_subsystems).
"""

import json
import re

import requests

from app.core import database as db
from app.ai.ai_assistant import _get_opencode_headers


def _config():
    s = db.get_all_settings()
    provider = (s.get("ai_provider") or "local").strip().lower()
    raw_base = s.get("ai_base_url", "")
    raw_model = s.get("ai_model", "")
    if provider == "opencode":
        base_url = raw_base if (raw_base and "openai.com" not in raw_base) else "https://opencode.ai/zen/v1"
        model = raw_model if (raw_model and raw_model != "gpt-4o-mini") else "big-pickle"
    else:
        base_url = raw_base or "https://api.openai.com/v1"
        model = raw_model or "gpt-4o-mini"
    return {
        "provider": provider,
        "base_url": base_url.rstrip("/"),
        "api_key": (s.get("ai_api_key") or "").strip(),
        "model": model,
        "temperature": float(s.get("ai_temperature") or 0.1),
    }


def is_ai_available():
    cfg = _config()
    if cfg["provider"] == "opencode":
        return True
    return cfg["provider"] in ("cloud", "openai") and bool(cfg["api_key"]) and bool(cfg["base_url"])


def _build_prompt(tables_data, fk_list):
    tables = sorted(tables_data.keys())
    lines = []
    fk_by_parent = {}
    for f in fk_list:
        fk_by_parent.setdefault(f["parent"], []).append(f["child"])
    for t in tables:
        fkids = fk_by_parent.get(t, [])
        rel = (", children: " + ", ".join(sorted(fkids))) if fkids else ""
        lines.append(f"- {t}{rel}")
    schema_txt = "\n".join(lines)
    return (
        "You are a database architecture analyst. Given the tables of a database "
        "and their foreign-key relations, design a small set of logical subsystems "
        "(modules) and assign every table to exactly one.\n"
        "- Group tables by business domain USING the actual table names and relations "
        "you see; do NOT invent domains with no matching tables.\n"
        "- Keys must be lowercase snake_case, e.g. auth, catalog, sales.\n"
        "- Every table in the list must appear exactly once in `mapping`.\n"
        "- Provide short Arabic (name_ar) and English (name_en) names, and a hex color.\n"
        "- Return STRICT JSON only, no markdown.\n\n"
        "TABLES WITH RELATIONSHIPS:\n" + schema_txt + "\n\n"
        "Return JSON in exactly this shape:\n"
        '{"subsystems":[{"key":"auth","name_ar":"...","name_en":"...",'
        '"description_ar":"...","description_en":"...","color":"#2563eb"}, ...],'
        '"mapping":{"TABLE_NAME":"key", ...}}'
    )


def _extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"```$", "", text.strip())
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object in response")
    # find the balanced closing brace
    depth = 0
    end = None
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        raise ValueError("unbalanced JSON")
    return json.loads(text[start:end])


def classify_schema(tables_data, fk_list):
    """Returns {"subsystems": [...defs], "mapping": {...}} or None on failure."""
    cfg = _config()
    if cfg["provider"] == "opencode":
        headers = _get_opencode_headers()
        timeout = 30
    elif cfg["provider"] in ("cloud", "openai") and cfg["api_key"]:
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {cfg['api_key']}"}
        timeout = 120
    else:
        return None
    tables = list(tables_data.keys())
    if not tables:
        return None

    prompt = _build_prompt(tables_data, fk_list)
    url = f"{cfg['base_url']}/chat/completions"
    body = {
        "model": cfg["model"],
        "temperature": cfg["temperature"],
        "messages": [
            {"role": "system", "content": "You produce strict JSON for structural analysis. No markdown."},
            {"role": "user", "content": prompt},
        ],
    }
    resp = requests.post(url, headers=headers, json=body, timeout=timeout)
    if resp.status_code != 200:
        return None
    try:
        content = resp.json()["choices"][0]["message"]["content"]
        data = _extract_json(content)
    except Exception:
        return None

    subsystems = data.get("subsystems") or []
    mapping = data.get("mapping") or {}
    if not isinstance(subsystems, list) or not isinstance(mapping, dict):
        return None

    defs = []
    seen = set()
    for s in subsystems:
        if not isinstance(s, dict):
            continue
        key = str(s.get("key", "")).strip().lower().replace(" ", "_")
        if not key or key in seen:
            continue
        seen.add(key)
        name_ar = str(s.get("name_ar") or s.get("name_en") or key)
        name_en = str(s.get("name_en") or key)
        color = str(s.get("color") or "#0891b2")
        if not re.match(r"^#[0-9a-fA-F]{6}$", color):
            color = "#0891b2"
        defs.append({
            "key": key,
            "name_ar": name_ar,
            "name_en": name_en,
            "description_ar": str(s.get("description_ar") or ""),
            "description_en": str(s.get("description_en") or ""),
            "color": color,
        })
    if not defs:
        return None

    valid_keys = set(d["key"] for d in defs)
    clean_mapping = {}
    for t in tables:
        key = str(mapping.get(t) or "").strip().lower().replace(" ", "_")
        if key not in valid_keys:
            key = "general"
        clean_mapping[t] = key
    # ensure a "general" def exists when used
    if "general" in valid_keys or any(k == "general" for k in clean_mapping.values()):
        if "general" not in seen:
            defs.append({
                "key": "general",
                "name_ar": "جداول عامة",
                "name_en": "General Tables",
                "description_ar": "جداول لا تنتمي لنظام فرعي محدد.",
                "description_en": "Tables not strongly tied to a subsystem.",
                "color": "#64748b",
            })
    return {"subsystems": defs, "mapping": clean_mapping}


def defs_labels(defs):
    return [d["key"] for d in defs]