"""Cheap heuristics to skip expensive memory LLM/embedding work."""

from __future__ import annotations

import re

# Signals the user is volunteering durable ops knowledge.
_PROPOSE_HINTS = re.compile(
    r"\b("
    r"heads\s+up|fyi|remember|always|from\s+now\s+on|prefer|preference|"
    r"fails?|failing|broken|outage|workaround|retry|protocol|exception|"
    r"note\s+that|keep\s+in\s+mind|tell\s+(people|staff|them)|"
    r"locally|for\s+this\s+clinic|our\s+clinic|"
    r"monday|tuesday|wednesday|thursday|friday|weekend|weekdays?|"
    r"hours|open(?:ing|s)?|clos(?:e|ed|ing)|schedule|"
    r"after\s+\d|units?\s+not\s+cases|show\s+stock"
    r")\b"
    # Time ranges like 8am-5pm / 08:00-17:00
    r"|\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\s*[-–to]+\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)\b"
    r"|\b\d{1,2}:\d{2}\s*[-–to]+\s*\d{1,2}:\d{2}\b",
    re.I,
)

# Same-day / temporary status — not durable memory.
_EPHEMERAL = re.compile(
    r"\b("
    r"today|tonight|this\s+(morning|afternoon|evening|week)|"
    r"right\s+now|currently|at\s+the\s+moment|just\s+now|"
    r"running\s+late|delayed|behind\s+schedule"
    r")\b",
    re.I,
)

# Recurring / sticky markers that override ephemeral dismissal.
_DURABLE_OVERRIDE = re.compile(
    r"\b("
    r"always|from\s+now\s+on|every\s+(monday|tuesday|wednesday|thursday|friday|week)|"
    r"prefer|preference|protocol|weekdays?|weekend|"
    r"monday\s+mornings?|tuesday\s+mornings?|"
    r"hours|units?\s+not\s+cases"
    r")\b",
    re.I,
)

# Typical one-off lookups / chit-chat — do not spend an LLM propose call.
_LOOKUP_OR_CHAT = re.compile(
    r"^\s*(thanks|thank\s+you|ok|okay|got\s+it|bye|good\s+morning|hi+|hello)\b"
    r"|^\s*what('s|\s+is|\s+are)\b"
    r"|^\s*(when|where|how)\s+(are|is|do|does|can)\b"
    r"|\b(how\s+much|fee|coverage|policy|checklist|do\s+we\s+(take|accept|cover))\b"
    r"|\bany\s+(known\s+)?issues?\b"
    r"|\bknown\s+issues?\b",
    re.I,
)

# Questions that may need memory recall (ops / local issues).
_RECALL_HINTS = re.compile(
    r"\b("
    r"issue|issues|problem|problems|fail|fails|failing|outage|workaround|"
    r"retry|monday|tuesday|wednesday|thursday|friday|weekend|weekdays?|"
    r"remember|prefer|preference|protocol|local|clinic|"
    r"hours|open(?:ing|s)?|clos(?:e|ed|ing)|schedule|"
    r"referral|referrals|inventory|stock|incident|ticket"
    r")\b",
    re.I,
)


def should_consider_proposing(question: str, answer: str = "") -> bool:
    """True only when an LLM memory proposal is worth the latency cost."""
    q = (question or "").strip()
    if len(q) < 12:
        return False
    # Lookups win first so "What are clinic hours?" does not propose.
    if _LOOKUP_OR_CHAT.search(q):
        return False
    # "appointments are delayed today" — temporary, not memory-worthy.
    if _EPHEMERAL.search(q) and not _DURABLE_OVERRIDE.search(q):
        return False
    if _PROPOSE_HINTS.search(q):
        return True
    # Answer-side hint alone is weak; require question not clearly a lookup.
    if answer and _PROPOSE_HINTS.search(answer):
        if _EPHEMERAL.search(q) and not _DURABLE_OVERRIDE.search(q):
            return False
        return True
    return False


def should_attempt_recall(question: str) -> bool:
    """Skip memory_read embedding/lookup for greetings and pure chit-chat."""
    q = (question or "").strip()
    if not q:
        return False
    if re.match(
        r"^(thanks|thank\s+you|ok|okay|got\s+it|bye|good\s+morning|hi+|hello)[.!]?\s*$",
        q,
        re.I,
    ):
        return False
    # Prefer recall when the question looks operational; otherwise still try
    # if it is longer than a greeting (cheap Redis list/keyword path).
    if _RECALL_HINTS.search(q):
        return True
    return len(q) >= 20
