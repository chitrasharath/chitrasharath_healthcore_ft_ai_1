from __future__ import annotations

# Documented tool / request error codes (spec §8.1).
AUTH_MISSING_TOKEN = "AUTH_MISSING_TOKEN"
AUTH_INVALID_TOKEN = "AUTH_INVALID_TOKEN"
AUTH_INSUFFICIENT_SCOPE = "AUTH_INSUFFICIENT_SCOPE"
INVENTORY_WRITE_FORBIDDEN = "INVENTORY_WRITE_FORBIDDEN"
VALIDATION_ERROR = "VALIDATION_ERROR"
NOT_FOUND = "NOT_FOUND"
UPSTREAM_TIMEOUT = "UPSTREAM_TIMEOUT"
UPSTREAM_ERROR = "UPSTREAM_ERROR"

MESSAGES: dict[str, str] = {
    AUTH_MISSING_TOKEN: "No bearer token presented. Provide Authorization: Bearer <token>.",
    AUTH_INVALID_TOKEN: "Access token is invalid, expired, or failed issuer/audience checks.",
    AUTH_INSUFFICIENT_SCOPE: "Token is valid but missing a required scope for this action.",
    INVENTORY_WRITE_FORBIDDEN: (
        "Inventory tool is read-only. Write operations are not permitted on this MCP server."
    ),
    VALIDATION_ERROR: "Tool input failed validation.",
    NOT_FOUND: "Requested resource was not found upstream.",
    UPSTREAM_TIMEOUT: "Upstream HTTP call timed out.",
    UPSTREAM_ERROR: "Upstream service returned an error or was unreachable.",
}

# Process exit codes (spec §8.2).
EX_OK = 0
EX_SOFTWARE = 1
EX_UNAVAILABLE = 69
EX_CONFIG = 78


def message_for(code: str, detail: str | None = None) -> str:
    base = MESSAGES.get(code, "An error occurred.")
    if detail:
        return f"{base} {detail}"
    return base
