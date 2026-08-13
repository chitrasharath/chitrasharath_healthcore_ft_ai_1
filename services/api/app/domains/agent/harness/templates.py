"""Deterministic refusal / redirect templates (verbatim for tests)."""

from __future__ import annotations

COMPANY_DOMAIN_SHORT = (
    "HealthCore front-desk support (insurance, appointments, fees, "
    "referrals, incidents, inventory)"
)

OVERRIDE_REFUSAL = (
    "I can't change or ignore my instructions. I'm here to help with "
    f"{COMPANY_DOMAIN_SHORT}. How can I help with that?"
)

PERSONAL_USE_BLOCK = (
    "I can't help with personal tasks unrelated to HealthCore. I can help with "
    f"{COMPANY_DOMAIN_SHORT}. What do you need there?"
)

COMPANY_REDIRECT = (
    "By the way — I'm here for HealthCore questions. How can I help with a policy, "
    "ticket, or inventory item today?"
)

SAFE_OUTPUT_REFUSAL = (
    f"I can't share that. I can help with {COMPANY_DOMAIN_SHORT} instead."
)

PHI_REFUSAL = (
    "For privacy (HIPAA / UK GDPR) I can't process patient-identifiable details. "
    "Please remove any names, ages, dates, IDs, or locations and ask me the general "
    "policy question — e.g. 'What's our late-cancellation policy for Medicaid patients?'"
)

# Prefixes used by the UI safety note and tests.
REFUSAL_TEMPLATES: tuple[str, ...] = (
    OVERRIDE_REFUSAL,
    PERSONAL_USE_BLOCK,
    PHI_REFUSAL,
    SAFE_OUTPUT_REFUSAL,
)
