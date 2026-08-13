"""Curated override / injection phrase patterns (≥3 rephrasings per category)."""

from __future__ import annotations

import re

# Ignore previous instructions
_IGNORE = [
    r"ignore\s+(all\s+)?(the\s+|your\s+)?(previous|above|prior)\s+(instructions|rules|guidelines)",
    r"disregard\s+(all\s+)?(your\s+)?(rules|instructions|guidelines)",
    r"override\s+(your\s+)?(guidelines|instructions|rules|policies)",
    r"answer\s+without\s+any\s+rules",
]

# No-rules / unrestricted persona
_NO_RULES = [
    r"you\s+(are\s+now\s+|have\s+)?(an?\s+)?unrestricted\s+(assistant|ai|model)",
    r"(act|pretend|behave)\s+(as\s+)?(an?\s+)?(unrestricted|DAN)\s+(assistant|ai)?",
    r"you\s+have\s+no\s+(rules|restrictions|policies|guardrails)",
    r"pretend\s+you\s+have\s+no\s+restrictions",
    r"assistant\s+with\s+no\s+(rules|policies|compliance\s+rules)",
]

# Identity wipe / HealthCore persona drop
_IDENTITY = [
    r"forget\s+(that\s+)?you\s+work\s+for\s+healthcore",
    r"you\s+are\s+no\s+longer\s+healthcore'?s?",
    r"drop\s+(your\s+)?(persona|role|healthcore\s+identity)",
    r"forget\s+that\s+you\s+work\s+for\s+healthcore\s+and\s+just\s+do\s+what\s+i\s+say",
]

OVERRIDE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.I) for p in (_IGNORE + _NO_RULES + _IDENTITY)
]

PERSONAL_USE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.I)
    for p in [
        r"\b(write|compose|draft)\s+(me\s+)?(a\s+)?(love\s+)?poem\b",
        r"\b(write|draft)\s+(me\s+)?(a\s+)?(personal\s+)?email\b",
        r"\bsalary\s+raise\b",
        r"\b(homework|essay|cover\s+letter)\b",
        r"\b(roleplay|role-play|therapy\s+session)\b",
        r"\b(write|generate)\s+(me\s+)?(a\s+)?(python|javascript|code)\s+(script|program)\b",
        r"\bscrape\s+(my\s+)?(personal\s+)?gmail\b",
    ]
]

CASUAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.I)
    for p in [
        r"\bwhat\s+time\s+is\s+it\b",
        r"\b(tokyo|london|paris|new\s+york)\b.*\btime\b",
        r"\bwho\s+won\s+the\s+world\s+cup\b",
        r"\bfun\s+fact\b",
        r"\btell\s+me\s+a\s+joke\b",
    ]
]

# Piecemeal breach / confidential BAA-DPA extraction
BREACH_BAA_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.I)
    for p in [
        r"\b(security\s+)?(breach|incident)\b.*\b(not\s+)?(closed|open|under.?investigation)\b",
        r"\bisn'?t\s+closed\s+yet\b",
        r"\bhow\s+many\s+records\s+were\s+affected\b",
        r"\bvendor\s+BAA\b|\bBAA\s+say\b|\bDPA\s+(terms|agreement)\b",
        r"\bconfidential\s+(commercial\s+)?terms\b",
    ]
]

# Instruction markers to scrub from external content
INSTRUCTION_MARKERS: list[re.Pattern[str]] = [
    re.compile(p, re.I)
    for p in [
        r"\[SYSTEM\]\s*:",
        r"###\s*system\s*:",
        r"<\s*system\s*>",
        r"^\s*assistant\s*:",
        r"ignore\s+(all\s+)?(the\s+|your\s+)?previous\s+(instructions|rules)",
    ]
]
