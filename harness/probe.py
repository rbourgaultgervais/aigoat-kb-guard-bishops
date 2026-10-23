#!/usr/bin/env python3
"""Probe one attack from attacks/attack-set.json against a local AI Goat.

Reads the payload from the data file (never hard-coded here), plants it in the
knowledge base as a regular customer, syncs it, then reports, per defense level,
whether the planted marker reaches the chatbot reply. It also runs AI Goat's own
retrieval trace at Level 2 to show what the RAG path's scan would do with the
same chunk. Output is observations and outcomes, not an attack recipe.

Usage:  python harness/probe.py KB-01
Target is the local instance only (see SCOPE.md).

"""
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

BASE = "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parent.parent


def call(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def main():
    attack_id = sys.argv[1] if len(sys.argv) > 1 else "KB-01"
    attacks = json.loads((ROOT / "attacks" / "attack-set.json").read_text())["attacks"]
    a = next(x for x in attacks if x["id"] == attack_id)

    _, login = call("POST", "/api/auth/login/", body={"username": "alice", "password": "password123"})
    token = login["token"]

    p = a["plant"]
    status, created = call("POST", "/api/knowledge-base/", token, {
        "title": p["title"], "content": p["content"],
        "category": p["category"], "trust_tier": p["trust_tier"],
    })
    print(f"[plant]  as customer 'alice': HTTP {status}, entry id {created.get('id')}, trust_tier '{p['trust_tier']}'")
    call("PATCH", "/api/knowledge-base/?rebuild=true", token)

    q, marker = a["benign_probe_question"], a["success_marker"]
    print(f"[probe]  question: {q!r}  marker: {marker!r}\n")

    print("  Customer-facing assistant (the chatbot), knowledge base on:")
    for level in (0, 1, 2):
        _, resp = call("POST", "/api/chat/", token,
                       {"message": q, "use_kb": True, "defense_level": level})
        reply = resp.get("reply", "") if isinstance(resp, dict) else str(resp)
        hit = marker in reply
        kb = resp.get("kb_used") if isinstance(resp, dict) else "?"
        verdict = ("ATTACK LANDED - the planted note reached the assistant" if hit
                   else "blocked      - the planted note did NOT reach the assistant")
        print(f"    Level {level}: {verdict}   (knowledge base still on: {kb})")

    print("\n  Same note, same setting, on AI Goat's OTHER path (the RAG console):")
    _, trace = call("POST", "/api/knowledge-base/trace", token, {"query": q, "defense_level": 2})
    ours = [c for c in trace.get("candidates", []) if p["title"] in (c.get("title") or "")]
    if not ours:
        print("    planted note not retrieved for this query")
    for c in ours:
        if c.get("excluded_by_control"):
            print(f"    DROPPED here by AI Goat's own control: {c.get('excluded_by_control')}")
        else:
            print(f"    let through here (included_in_context={c['included_in_context']})")
    print(f"    controls AI Goat applied on this path: {trace.get('controls_applied')}")


if __name__ == "__main__":
    main()
