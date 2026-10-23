# Authorization and scope

The rules of engagement for all testing in this repository. Every result here was produced under
this document. Crossing anything in it is a new decision that stops the work until the team agrees.

Written 2026-10-13, for the Bishop's University AI Cybersecurity Challenge 2026.

## What is being tested

**AI Goat v2.0** ([AISecurityConsortium/AIGoat](https://github.com/AISecurityConsortium/AIGoat)),
the open-source, deliberately vulnerable AI application that the Bishop's University Computer
Science department distributed for this competition. It describes its own vulnerabilities as
"features, not bugs" and is built to be attacked for learning.

## Why this is authorized

- The CS department provided this application for the competition. Attacking it is its intended use.
- Each team member runs their own copy on their own hardware. It is nobody else's service.
- It runs bound to `127.0.0.1`, reachable only from the machine it runs on, and is never exposed
  to a network or the internet. The application's own README says: "Do not expose it to the internet."
- No real people, accounts or third-party systems are involved. Users are seeded demo rows, card
  numbers are fake, and a simulated data-exfiltration email is a row written to a local database
  file. Nothing leaves the machine.

## In scope

- The local AI Goat instance running on a team member's own computer, over `127.0.0.1` only.
- Every attack surface the application ships: the chatbot, the knowledge base (RAG), the agent,
  and the MCP surfaces.
- Reading the application's own source to understand how its defenses work.

## Out of scope

- Any AI Goat instance that is not our own local copy: a public demo, a hosted version, or a
  teammate's machine reached over a network.
- Exposing the application to a network or the internet, or binding it to anything other than
  `127.0.0.1`.
- Any system, service or account not listed as in scope, including live third-party AI services.
  Using a commercial AI model to help write attack text is in scope; pointing an attack at one is
  not.
- Acting on any finding against a real target. Findings here are described and measured.

Anything outside this list is a new decision for the whole team, made before the work starts.

## Attack payloads are benign by design

Every attack in [`attacks/attack-set.json`](attacks/attack-set.json) succeeds only when a harmless
unique marker proves the planted content reached or steered the model. None of them leaks real
data, exfiltrates anything, or damages the application. The payload used in the live demonstration
plants a fictional store notice.

This is deliberate. The finding is that planted content reaches the model on a path with no
retrieval scan, and a harmless marker demonstrates that as well as a damaging payload would, with
nothing to clean up afterward.

## Data handling

- All testing data (planted documents, chat logs, simulated exports) stays on the local machine.
- Attack strings are published here as a competition deliverable, in the attack-set data file.
  Observations and outcomes are recorded; reusable attack recipes against anything other than this
  local application are not.
- Nothing from the local application is copied to a public place without the team agreeing it is
  safe to publish.

