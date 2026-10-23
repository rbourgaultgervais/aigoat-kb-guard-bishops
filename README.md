# AI Goat KB Guard

A retrieval-stage defense against knowledge-base poisoning in AI Goat's customer-facing
chatbot.

Team entry for the **Bishop's University AI Cybersecurity Challenge 2026**.
Target application: [AI Goat v2.0](https://github.com/AISecurityConsortium/AIGoat), the
deliberately vulnerable AI application distributed for the challenge.

Everything here runs against one local AI Goat instance bound to `127.0.0.1`. The rules of
engagement are in [`SCOPE.md`](SCOPE.md).

---

## The threat

AI Goat's shop assistant, Cracky, answers customers from a knowledge base of product facts,
policies and FAQs. **Any logged-in customer can write to that knowledge base.**

So a customer can plant a document that contains instructions instead of information. The
assistant reads those instructions as though the store wrote them, and follows them for every
customer who asks afterward. The attacker never speaks to the assistant; they leave something
behind, and it harms everyone who comes later.

This is indirect prompt injection (OWASP **LLM01**) combined with weak trust controls on the
vector store (OWASP **LLM08**, Vector and Embedding Weaknesses). It is realistic because the
content that fills a production knowledge base often comes from customers themselves, through
reviews, feedback forms and support tickets.

## What we found

AI Goat ships three defense levels: **0 Vulnerable**, **1 Hardened** (input validation, intent
classification, output filtering), and **2 Guardrailed** (level 1, tightened, plus Unicode and
Base64 checks, NVIDIA NeMo Guardrails, and a **retrieval injection scan**).

**F1. The chatbot path skips the retrieval scan.** AI Goat's `retrieval.injection_scan` is wired
into the RAG console path and absent from the chatbot path that customers use. We planted one
document and asked an ordinary question. The planted content reached the assistant at Level 0,
Level 1 and Level 2. The identical chunk, sent through the RAG console path at Level 2, was
dropped by the scan. Same chunk, same setting: blocked on one path, through on the other.

**F2. Any customer can poison the knowledge base, and forge its provenance.** As an ordinary
customer we created a knowledge-base entry stamped with the top `system` trust tier, and we
rewrote another customer's entry. Only deletion required an admin. The attacker in this threat
model is therefore any logged-in customer, and a planted document can be made to look official.

## Where the gap is

```
  customer question
         |
         v
  [ L1/L2 input validation, intent classifier ]
         |
         v
  retrieve chunks from ChromaDB  <-- knowledge base, writable by ANY customer (F2)
         |
         +--> RAG console path  :  retrieval.injection_scan  -->  poisoned chunk DROPPED
         |
         +--> chat.cracky path  :  no retrieval scan         -->  poisoned chunk REACHES
                                                                   the prompt          (F1)
```

## The defense

[`defense/kb_guard.py`](defense/kb_guard.py), one dependency-free module, placed at the
retrieval stage of the chatbot path:

```
  retrieve chunks from ChromaDB
         |
         v
  [ kb_guard.scan_chunks ]  <-- our control, same stage, on the path customers use
         |                       kept chunks continue; dropped chunks are logged with a reason
         v
  token budget  ->  prompt  ->  model
         |
         v
  [ L1/L2 output filtering ]
```

Three design choices carry the work:

1. **It inspects content, and scores three independent signals** (instruction-override phrasing,
   role or policy override framing, and a directive aimed at the assistant paired with an echo
   instruction). A chunk is dropped when any signal fires, so rewording one phrase does not slip
   a directive through.
2. **It never trusts a chunk's claimed trust tier**, because F2 shows any customer can set that
   tier to `system`.
3. **It normalizes before matching**, stripping invisible format characters and applying NFKC, so
   zero-width padding and Unicode lookalikes do not evade the signals.

Its input is text that was retrieved rather than text the customer typed, which is the stage where
the distinction between information and instruction still exists.

The guard is **off unless `AIGOAT_KB_GUARD=1`**, so a clone with the hook applied behaves exactly
like stock AI Goat until the flag is set. The hook is six lines.
[`defense/INTEGRATION.md`](defense/INTEGRATION.md) has the patch and the reversal.

## Results

Chatbot surface (`chat.cracky`), knowledge base on. Attack set: 3 attacks (indirect injection and
trust-tier spoof). Benign set: 5 ordinary customer questions. Local instance, Mistral 7B, RTX 3060.
Levels-only measured across eight runs; guard-on across two.

| | Level 0 | Level 1 | Level 2 |
|---|---|---|---|
| **Attack bypass, AI Goat's levels only** (24 trials) | 23/24 (96%) | 21/24 (88%) | **18/24 (75%)** |
| **Attack bypass, with our guard** (6 trials) | 0/6 (0%) | 0/6 (0%) | **0/6 (0%)** |
| Benign blocked, with our guard | 0/10 | 0/10 | 0/10 |
| Mean latency, with our guard | 3.2 s | 2.4 s | 3.0 s |

One control, on the path customers use, takes knowledge-base poisoning from three quarters of
trials landing at AI Goat's strongest setting down to none at any level, with no ordinary question
blocked and no latency cost.

The zero is a property of the mechanism rather than a lucky sample: the guard is deterministic, and
the backend log records the poisoned chunk dropped by content on every attack call, before the model
received it.

Full tables and per-run detail: [`results/comparison.md`](results/comparison.md),
[`results/levels-only-trials.md`](results/levels-only-trials.md).

## Limits, stated plainly

- **The guard is a content scanner.** A patient attacker who rewords an instruction to avoid all
  three signals could still get a chunk through. Real depth is layers, and this is one layer.
- **We do not claim the levels-only trend as a real effect.** The movement from 96% to 75% comes
  almost entirely from one nondeterministic attack, and 24 trials cannot separate that from
  sampling noise. The claim we do make is the guard-on column.
- **One surface, one attack family.** AI Goat v2.0 ships 46 labs across the LLM, Agentic and MCP
  top 10. This is a vertical slice, measured end to end, built to test the approach before taking
  it wider.

The layered form this points to: quarantine documents at ingestion, mark retrieved text as
untrusted to the model, enforce the trust tier server-side so a customer cannot claim `system`,
scan the output for leaks, and register the guard as a level-aware control in AI Goat's own defense
profile in place of an environment flag. Each layer catches what the one before it misses.

## Repository layout

| Path | What |
|---|---|
| [`defense/kb_guard.py`](defense/kb_guard.py) | the security solution, 76 lines, no dependencies |
| [`defense/INTEGRATION.md`](defense/INTEGRATION.md) | how to apply it to an AI Goat clone, and how to reverse it |
| [`attacks/attack-set.json`](attacks/attack-set.json) | the attack set, tagged by family, OWASP risk and surface |
| [`attacks/benign-set.json`](attacks/benign-set.json) | ordinary customer questions, for measuring over-blocking |
| [`harness/probe.py`](harness/probe.py) | runs one attack at all three levels, plus AI Goat's RAG trace for comparison (reproduces F1) |
| [`harness/probe_authz.py`](harness/probe_authz.py) | knowledge-base write authorization (reproduces F2) |
| [`harness/baseline.py`](harness/baseline.py) | the full table: every attack and every benign question at each level |
| [`results/`](results/) | measured results, before and after |
| [`SETUP.md`](SETUP.md) | environment, starting AI Goat, applying the guard |
| [`DEMO.md`](DEMO.md) | the live demonstration, reproducible step by step |
| [`SCOPE.md`](SCOPE.md) | rules of engagement for all testing here |

## Getting started

1. [`SETUP.md`](SETUP.md), to get AI Goat and the guard running locally.
2. [`DEMO.md`](DEMO.md), to reproduce the attack and the defense end to end.
3. `python harness/probe.py KB-01`, for the shortest path to finding F1.

Attack payloads are **benign by design**. An attack counts as successful only when a harmless
unique marker proves the planted content reached the model. None of them leaks real data, and the
demo payload is a fictional store notice.

## Tooling

Python 3.11, FastAPI and ChromaDB (AI Goat's own stack), Ollama with Mistral 7B. An AI coding
assistant was used throughout the build; every result in this repository was produced by running
the code and observing the output.

## Team

Raphael Bourgault Gervais and Arsalan Nazary, Bishop's University.

Licensed MIT ([`LICENSE`](LICENSE)). The target application, AI Goat, is a separate project under
its own license and is not vendored here.
