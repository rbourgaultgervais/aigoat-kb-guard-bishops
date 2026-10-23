#!/usr/bin/env python3
"""Probe H2: knowledge-base write authorization on a local AI Goat.

Checks three things a customer can or cannot do to the knowledge base:
  (a) create an entry while spoofing a higher trust tier,
  (b) edit another customer's entry,
  (c) delete an entry (expected to be the one admin-gated action).

Observations only. Local instance only (see SCOPE.md).
Usage:  python harness/probe_authz.py

"""
import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"


def call(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, None


def token_for(user):
    _, r = call("POST", "/api/auth/login/", body={"username": user, "password": "password123"})
    return r["token"]


def entry_by_id(token, eid):
    _, r = call("GET", "/api/knowledge-base/", token)
    return next((d for d in r["documents"] if d["id"] == eid), None)


def main():
    alice, bob = token_for("alice"), token_for("bob")

    # (a) customer creates an entry claiming the top "system" trust tier
    _, created = call("POST", "/api/knowledge-base/", alice, {
        "title": "Authz probe entry", "content": "original content, by alice",
        "category": "promotions", "trust_tier": "system",
    })
    eid = created["id"]
    row = entry_by_id(alice, eid)
    print(f"(a) customer 'alice' created entry {eid}: "
          f"trust_tier='{row['trust_tier']}', is_user_injected={row['is_user_injected']}, owner_id={row['owner_id']}")
    print(f"    -> trust-tier spoofing {'POSSIBLE' if row['trust_tier'] == 'system' else 'blocked'}")

    # (b) a different customer edits alice's entry
    status, res = call("PUT", f"/api/knowledge-base/{eid}/", bob,
                       {"content": "REWRITTEN by bob, who does not own this entry"})
    after = entry_by_id(alice, eid)
    changed = after["content"].startswith("REWRITTEN by bob")
    print(f"(b) customer 'bob' edits alice's entry {eid}: HTTP {status}; content changed = {changed}")
    print(f"    -> cross-customer edit {'POSSIBLE' if changed else 'blocked'}")

    # (c) a customer tries to delete it (expected admin-gated)
    status, _ = call("DELETE", f"/api/knowledge-base/{eid}/", bob)
    print(f"(c) customer 'bob' deletes entry {eid}: HTTP {status}")
    print(f"    -> delete {'gated to admin (403)' if status == 403 else 'allowed for customers'}")


if __name__ == "__main__":
    main()
