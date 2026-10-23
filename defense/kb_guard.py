"""Retrieval-stage knowledge-base guard (our defense).

AI Goat ships a retrieval injection scan, but only the RAG console path runs it;
the customer-facing chatbot places retrieved chunks in the prompt unscanned
(finding F1). This module is the missing control: scan each retrieved chunk for
content that reads like an instruction to the assistant, and drop it before it
reaches the model. It never trusts a chunk's claimed trust tier, since any
customer can set that to "system" (finding F2).

It is deliberately stronger than a fixed phrase list: it scores each chunk on
several independent signals and drops the chunk if any fires, so rewording one
phrase does not slip a directive through. The trade-off, higher false positives
on chunks that merely quote an instruction, is what the benign set measures.

Pure Python, no dependencies, so it drops into the app or runs in a test.

"""
from __future__ import annotations

import re
import unicodedata

# Signals that a retrieved chunk is trying to instruct the assistant rather than
# inform the customer. A chunk is dropped if any one fires.
_DIRECTIVE = re.compile(
    r"\b(?:ignore|disregard|forget|override|bypass)\b.{0,40}"
    r"\b(?:previous|prior|above|earlier|all|your)\b.{0,20}"
    r"\b(?:instruction|instructions|rules?|context|prompt|guidelines?|message)\b",
    re.I | re.S,
)
_IMPERATIVE_TO_ASSISTANT = re.compile(
    r"\b(?:you|assistant|cracky)\b.{0,20}\b(?:must|should|need to|have to|will|always|never)\b",
    re.I | re.S,
)
_ECHO_DIRECTIVE = re.compile(
    r"\b(?:include|append|add|output|print|repeat|insert|emit)\b.{0,40}"
    r"\b(?:code|token|string|text|phrase|reference|verification)\b",
    re.I | re.S,
)
_ROLE_FRAME = re.compile(
    r"\b(?:you are now|from now on|act as|pretend|new instructions?\s*:|system\s*:|"
    r"\[/?inst\]|policy update|official store policy|all restrictions)\b",
    re.I,
)


def _normalize(text: str) -> str:
    # strip zero-width and other invisible characters, normalize, collapse space
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text)


def inspect(chunk: str) -> str | None:
    """Return a short reason the chunk looks instruction-like, or None if clean."""
    t = _normalize(chunk or "")
    if _DIRECTIVE.search(t):
        return "instruction-override phrasing"
    if _ROLE_FRAME.search(t):
        return "role or policy override framing"
    if _IMPERATIVE_TO_ASSISTANT.search(t) and _ECHO_DIRECTIVE.search(t):
        return "directive aimed at the assistant"
    return None


def scan_chunks(chunks: list[str]) -> tuple[list[str], list[tuple[str, str]]]:
    """Split retrieved chunks into (kept, dropped). dropped is (chunk, reason)."""
    kept: list[str] = []
    dropped: list[tuple[str, str]] = []
    for c in chunks:
        reason = inspect(c)
        if reason:
            dropped.append((c, reason))
        else:
            kept.append(c)
    return kept, dropped
