# Applying the KB guard to an AI Goat clone

The defense is one module, `kb_guard.py`, plus a small flagged hook in AI Goat's
chatbot path. It is off unless `AIGOAT_KB_GUARD=1`, so a clone with the hook
applied behaves exactly like stock AI Goat until the flag is set.

## Steps

1. Copy `defense/kb_guard.py` into the clone at `app/defense/kb_guard.py`.
2. In `app/surfaces/chat_cracky.py`, right after the retrieved chunks are built:

   ```python
   chunks = [r.get("content", "") for r in results if r.get("content")]
   ```

   insert, before the `truncate_chunks_to_budget` call:

   ```python
   import os
   if os.getenv("AIGOAT_KB_GUARD") == "1":
       from app.defense.kb_guard import scan_chunks
       chunks, dropped = scan_chunks(chunks)
       if dropped:
           logger.info("KB guard dropped %d chunk(s): %s",
                       len(dropped), [reason for _, reason in dropped])
   ```

3. Restart the backend with the flag to enable it.

   Linux or macOS:

   ```bash
   AIGOAT_KB_GUARD=1 ./venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

   Windows PowerShell, which has no inline environment-variable prefix:

   ```powershell
   $env:AIGOAT_KB_GUARD="1"
   .\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

## Reversibility

The hook changes nothing when the flag is unset. On the demo machine a backup of
the original file is kept at `app/surfaces/chat_cracky.py.orig`; restore it to
remove the hook entirely.

## Measuring

With the flag set, `harness/baseline.py results/with-defense.md "..."` produces the
guard-on table; without it, the same script produces the baseline. `results/comparison.md`
holds both.

## Note for the final build

This is the demo integration: a per-request env flag. A cleaner form registers the
scan as a proper retrieval-stage control in AI Goat's own defense profile for
`chat.cracky`, so it switches with the defense level instead of an env var. The
behaviour measured here is the same either way.
