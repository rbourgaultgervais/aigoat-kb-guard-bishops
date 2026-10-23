# Results: knowledge base poisoning on the chatbot, before and after our defense

Chatbot surface (`chat.cracky`), knowledge base on. Attack set: KB-01, KB-02, KB-03 (indirect injection and trust-tier spoof). Benign set: 5 ordinary customer questions. Local instance, Mistral 7B, RTX 3060. Measured 2026-10-13, re-measured across seven further runs on 2026-10-22.

| | Level 0 | Level 1 | Level 2 |
|---|---|---|---|
| **Attack bypass, AI Goat's levels only** (8 runs, 24 trials) | 23/24 (96%) | 21/24 (88%) | **18/24 (75%)** |
| **Attack bypass, with our KB guard** (2 runs, 6 trials) | 0/6 (0%) | 0/6 (0%) | **0/6 (0%)** |
| Benign blocked, AI Goat's levels only | 0/40 | 0/40 | 0/40 |
| Benign blocked, with our KB guard | 0/10 | 0/10 | 0/10 |
| Mean latency, levels only | 2.0-4.5 s | 2.5-3.6 s | 2.0-3.8 s |
| Mean latency, with our guard | 3.2 s | 2.4 s | 3.0 s |

Per-run detail for the levels-only row: [`levels-only-trials.md`](levels-only-trials.md).

## What it says

- AI Goat's own hardening does not stop this attack on the chatbot path. At Level 2, the strongest setting, three quarters of attack trials still reach the model.
- The levels do appear to help a little, 96% down to 75%, and we are careful about that number: the whole movement comes from one attack (KB-02) that is nondeterministic, and it bypassed at all three levels when run on its own. Twenty-four trials cannot separate a real effect from sampling noise.
- Our guard, one retrieval-stage control, takes bypass to 0% at every level, including Level 0, and that zero is deterministic rather than sampled.
- It adds no false positives: all five benign questions are still answered at every level.
- It adds no measurable latency: the scan is a fast local pattern check, within the run-to-run noise of the model's own reply time.

## Why the 0%

The guard is deterministic. The backend log shows it dropped the poisoned chunk on all nine attack trials (three attacks x three levels), by three independent signals: instruction-override phrasing (KB-01), a directive aimed at the assistant (KB-02), and policy-override framing (KB-03). The model never receives the planted text, so the outcome does not depend on the model's randomness.

## Limitations

- The levels-only column is now averaged over eight runs (`levels-only-trials.md`), which is what the earlier single-trial version of this table could not support. The guard-on column rests on two full-suite runs plus the per-chunk drop recorded in the backend log on every attack call.
- The guard is a content scanner. A sufficiently reworded instruction that avoids all three signals could still pass; this is the limitation to show openly in the demo, and the reason a defense should not rely on a single pattern layer.
