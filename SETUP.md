# Setup

How to get a local AI Goat running, apply the guard, and run the measurement. Written from
full cold starts on Windows 10 and verified by running every command below.

Scope for all of it is [`SCOPE.md`](SCOPE.md): one local clone, bound to `127.0.0.1`, never
exposed to a network.

## Two paths you substitute throughout

| Name | What it is |
|---|---|
| `CLONE` | your AI Goat clone, the folder with `app/`, `frontend/`, `requirements.txt` and `venv/` directly inside it |
| `REPO` | your clone of this repository |

A `git clone` of AI Goat into `C:\ai-goat` puts `CLONE` at `C:\ai-goat`. Unpacking the
distributed ZIP adds one level, so `CLONE` becomes something like
`C:\ai-goat\AIGoat-main`. Check which you have before you start.

## Requirements

| | |
|---|---|
| AI Goat | [AISecurityConsortium/AIGoat](https://github.com/AISecurityConsortium/AIGoat) v2.0, cloned locally |
| Python | 3.11, in the clone's `venv/`, with the clone's `requirements.txt` installed |
| Node | 18 or newer, with `frontend/node_modules` installed |
| Ollama | installed, with `mistral` pulled (`ollama pull mistral`) |
| Hardware | 8 GB RAM minimum. A GPU takes chat replies from 10 to 30 seconds down to about 3 |

The guard itself needs nothing. `defense/kb_guard.py` is pure Python with no imports beyond
`re` and `unicodedata`, so it runs anywhere Python 3.9 or newer does.

## Do not use the shipped `scripts/start.sh`

Two reasons, and the second one matters on every platform:

1. It is written for Linux and macOS. It needs `lsof` and a `venv/bin` layout, neither of
   which exists on Windows.
2. **It starts the backend with `--host 0.0.0.0`,** which binds every interface. Our scope
   requires `127.0.0.1` only, and AI Goat's own README says not to expose it.

Start the processes by hand, as below.

## Starting, three terminals

### 1. The model

Confirm the model is present:

```
ollama list
```

It should list `mistral:latest`. On Windows the Ollama app already serves on
`127.0.0.1:11434` as soon as any `ollama` command runs, so `ollama serve` returns a bind
error and is unnecessary. On Linux and macOS, where Ollama runs as a service,
`systemctl status ollama` is the equivalent check.

### 2. The backend, port 8000

Linux or macOS:

```bash
cd CLONE
./venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level info
```

Windows PowerShell:

```powershell
cd CLONE
CLONE\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level info
```

Call `python.exe` by its full path on Windows. PowerShell's default execution policy
(`Restricted`) blocks `Activate.ps1`, and a venv's `python.exe` finds its own packages with
no activation, so the full path works in any shell with no machine settings changed. A bare
`python` is likely to resolve to a different interpreter that has no uvicorn.

Wait for `Uvicorn running on http://127.0.0.1:8000`, about 4 seconds. Confirm at
`http://127.0.0.1:8000/docs`. The first *chat reply* after a start takes about 15 seconds,
because the model and the embeddings load then; every reply after it takes about 3.

### 3. The frontend, port 3000

Linux or macOS:

```bash
cd CLONE/frontend
HOST=127.0.0.1 PORT=3000 BROWSER=none npm start
```

Windows PowerShell:

```powershell
cd CLONE\frontend
$env:HOST="127.0.0.1"; $env:PORT="3000"; $env:BROWSER="none"
npm.cmd start
```

`npm.cmd` rather than `npm` on Windows, for the same execution-policy reason: `npm` resolves
to `npm.ps1`. Wait for `Compiled successfully!`, then open `http://127.0.0.1:3000`.

If it offers to use another port, answer **n**. Free port 3000 instead and start again, since
the rest of this document assumes 3000.

### Confirm the binding before you test anything

```powershell
netstat -ano | findstr "LISTENING" | findstr ":8000 :3000"
```

```bash
ss -ltnp | grep -E ':8000|:3000'
```

Both lines must show `127.0.0.1`. **If either shows `0.0.0.0`, stop and restart it bound to
localhost**; the application would otherwise be reachable from the network, which
[`SCOPE.md`](SCOPE.md) forbids.

### Seeded accounts

Customers `alice`, `bob`, `charlie`, `frank`, all with `password123`. Staff `admin` with
`admin123`; the admin password differs because `scripts/seed.py` sets it. The attack is run as
an ordinary customer throughout, which is the point of finding F2.

Stop each process with Ctrl-C. `scripts/stop.sh` is bash-only, like `start.sh`.

## Turning the knowledge base on

Cracky ignores the knowledge base until it is switched on. In the navigation bar,
**Console → RAG**, then enable **Knowledge Base integration with Cracky AI**. The setting
lives in the browser's `localStorage`, so it is per browser rather than per account, and it
survives restarts.

The **Sync** button on that page re-embeds documents into ChromaDB. **A new document is not
retrievable until it is synced.** Forgetting Sync after planting is the single most common
reason a reproduction attempt shows nothing.

## Two defense switches, which are independent

**AI Goat's levels 0, 1 and 2** are per request: the toggle in the header for browser messages,
or the `defense_level` field in the chat request body for scripts. No restart. The toggle is
hidden from the `admin` account and visible to customers.

**Our KB guard** is an environment variable read when the backend process starts, so it is
chosen at launch and cannot change while the process runs.

Linux or macOS:

```bash
AIGOAT_KB_GUARD=1 ./venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Windows PowerShell, which has no inline environment-variable prefix, so this is two lines:

```powershell
$env:AIGOAT_KB_GUARD="1"; "GUARD=$env:AIGOAT_KB_GUARD"
CLONE\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level info
```

The `"GUARD=$env:AIGOAT_KB_GUARD"` echo is worth keeping. The flag's state is visible only at
launch, and a stale variable from an earlier run is the easiest way to measure the wrong thing.
To turn the guard off, use `Remove-Item env:AIGOAT_KB_GUARD` (PowerShell) or a fresh shell.

The guard runs at **every** level, including Level 0. Seeing the application resist the attack
while the header reads "L0 Vulnerable" is correct: the guard is our control and AI Goat's UI
has no knowledge of it. [`defense/INTEGRATION.md`](defense/INTEGRATION.md) describes the
cleaner form that would register it as a level-aware control instead.

Both `POST /api/chat/` and `POST /api/chat/stream` reach the guard, because the hook sits inside
`prepare_chat` in `app/surfaces/chat_cracky.py` and both endpoints call it. The harness uses the
first; the browser uses the second.

## Applying the guard to your clone

[`defense/INTEGRATION.md`](defense/INTEGRATION.md) is the patch: copy one file, insert six lines
in `app/surfaces/chat_cracky.py`, restart with the flag. The hook changes nothing while the flag
is unset, so a patched clone is still stock AI Goat until you switch it on.

## Running the measurement

From `REPO`, with the backend running:

```bash
# one attack at all three levels, plus AI Goat's RAG trace for the same chunk (reproduces F1)
python harness/probe.py KB-01

# knowledge-base write authorization (reproduces F2)
python harness/probe_authz.py

# the full table: every attack and every benign question at each level
python harness/baseline.py results/your-run.md "levels only"
```

On Windows, call the clone's interpreter by full path, since it is the one with the
dependencies: `CLONE\venv\Scripts\python.exe harness\probe.py KB-01`.

Use your own output filename. Passing `results/baseline.md` overwrites the committed table.

For the before-and-after, run `baseline.py` once with the guard off and once with it on.
A `baseline.py` run is 24 chat calls, measured at 71 and 80 seconds on an RTX 3060.

## Reset to a clean state

Each probe leaves its planted document behind. **Reset before any measured run**, or the
previous run's plant is still in the index.

Stop the backend first; the database file is locked while it runs.

```powershell
cd CLONE
Remove-Item aigoat.db -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force chroma_db -ErrorAction SilentlyContinue
CLONE\venv\Scripts\python.exe -m alembic upgrade head
CLONE\venv\Scripts\python.exe -m scripts.seed
```

```bash
cd CLONE
rm -f aigoat.db && rm -rf chroma_db
./venv/bin/python -m alembic upgrade head
./venv/bin/python -m scripts.seed
```

Expect `Seed completed successfully.` A `Cannot find path ... chroma_db` message is fine; it
means the store was already gone.

**What this destroys:** the local test database only. It holds seeded demo rows, fake products
and fake card numbers, and `scripts.seed` rebuilds all of it. Nothing of value is in it, and
nothing outside `CLONE` is touched.

After a reset the vector store is empty and a fresh browser session starts at Level 0 with the
knowledge base off, so re-enable the integration and press Sync again.

## Known quirks

**Broken product images on Windows.** AI Goat ships media files whose names contain double
quotes, for example `The "Code Break" Hacker Cap (Hacker Cap).png`. Windows forbids `"` in file
names, so the file cannot exist and `staticfiles` raises `OSError: [WinError 123]` whenever the
browser requests it. The backend log fills with the traceback. It is harmless to the chat, the
knowledge base and every result here, and it shows up as missing images in the shop.

**Outbound calls on first knowledge-base use.** The backend contacts `huggingface.co` for
`sentence-transformers/all-MiniLM-L6-v2` metadata, logs a 404 and a warning, then loads the
cached weights and continues. Nothing of ours leaves the machine. The call fires on the first
knowledge-base use rather than at launch, so to test a cold start with the network disconnected
you have to run a probe, not just start the backend.

**The level and the guard live in different places.** The level lives in the browser session and
the guard lives in the backend process, so a backend restart changes one and leaves the other.
Check the header before measuring anything by hand.
