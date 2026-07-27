from __future__ import annotations

import logging
import re
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from app.domains.agent.tools.base import api_url, request_with_retry

logger = logging.getLogger(__name__)

# Dropped from multi-token matching so classifier phrases still hit product names.
_HINT_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "and",
        "or",
        "how",
        "many",
        "much",
        "do",
        "we",
        "have",
        "in",
        "stock",
        "any",
        "our",
        "item",
        "items",
        "product",
        "products",
        "supply",
        "supplies",
    }
)


class InventoryToolInput(BaseModel):
    name_hint: str | None = None


class InventoryToolResult(BaseModel):
    source: Literal["inventory_tool"] = "inventory_tool"
    ok: bool
    products: list[dict[str, Any]] = Field(default_factory=list)
    matched: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None
    empty: bool = False


def _token_variants(token: str) -> set[str]:
    """Casefolded forms including a light singular (masks → mask)."""
    t = token.casefold().strip()
    if not t:
        return set()
    variants = {t}
    if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
        variants.add(t[:-1])
    return variants


def _haystack_has_token(haystack: str, token: str) -> bool:
    return any(v in haystack for v in _token_variants(token))


def _hint_tokens(hint: str) -> list[str]:
    parts = re.split(r"[^\w]+", hint.casefold())
    return [p for p in parts if p and p not in _HINT_STOPWORDS]


def _product_matches_hint(product: dict[str, Any], hint: str) -> bool:
    name = str(product.get("name") or "").casefold()
    sku = str(product.get("sku") or "").casefold()
    folded = hint.casefold().strip()
    if not folded:
        return False
    # Exact substring (spec baseline).
    if folded in name or folded in sku:
        return True
    # Token match: every significant token appears (handles plural drift).
    tokens = _hint_tokens(folded)
    if not tokens:
        return False
    return all(
        _haystack_has_token(name, tok) or _haystack_has_token(sku, tok)
        for tok in tokens
    )


def _match_products(
    products: list[dict[str, Any]], name_hint: str | None
) -> list[dict[str, Any]]:
    if not name_hint:
        return []
    return [p for p in products if _product_matches_hint(p, name_hint)]


def run_inventory_tool(
    inp: InventoryToolInput, *, auth_token: str | None
) -> InventoryToolResult:
    """Call inventory products HTTP API. Never raises into the graph."""
    headers: dict[str, str] = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    try:
        url = api_url("/api/v1/inventory/products")
        response = request_with_retry(
            "GET", url, headers=headers or None
        )
        if response.status_code < 200 or response.status_code >= 300:
            return InventoryToolResult(
                ok=False, error=f"http_{response.status_code}"
            )
        products = response.json()
        if not isinstance(products, list):
            return InventoryToolResult(ok=False, error="transport")
        matched = _match_products(products, inp.name_hint)
        empty = (not products) or (bool(inp.name_hint) and not matched)
        return InventoryToolResult(
            ok=True,
            products=products,
            matched=matched,
            empty=empty,
        )
    except httpx.TimeoutException:
        return InventoryToolResult(ok=False, error="timeout")
    except httpx.TransportError:
        logger.warning("Inventory tool transport error", exc_info=True)
        return InventoryToolResult(ok=False, error="transport")
    except Exception:
        logger.warning("Inventory tool unexpected error", exc_info=True)
        return InventoryToolResult(ok=False, error="transport")
