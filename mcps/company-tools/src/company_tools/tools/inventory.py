from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from company_tools import auth, errors
from company_tools.downstream import (
    DownstreamError,
    inventory_url,
    request_json,
    resolve_downstream_token,
)
from company_tools.logging import with_invocation_log
from company_tools.request_context import get_current_request

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

_WRITE_FIELDS = frozenset(
    {
        "quantity",
        "delta",
        "set_stock",
        "stock",
        "create",
        "update",
        "delete",
        "action",
        "write",
    }
)


class QueryInventoryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name_hint: str | None = None
    product_id: int | None = None


class InventoryToolOutput(BaseModel):
    ok: bool
    products: list[dict[str, Any]] = Field(default_factory=list)
    matched: list[dict[str, Any]] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None


def _token_variants(token: str) -> set[str]:
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
    if folded in name or folded in sku:
        return True
    tokens = _hint_tokens(folded)
    if not tokens:
        return False
    return all(
        _haystack_has_token(name, tok) or _haystack_has_token(sku, tok)
        for tok in tokens
    )


def match_products(
    products: list[dict[str, Any]], name_hint: str | None
) -> list[dict[str, Any]]:
    if not name_hint:
        return []
    return [p for p in products if _product_matches_hint(p, name_hint)]


def _err(code: str, detail: str | None = None) -> dict[str, Any]:
    return {
        "ok": False,
        "products": [],
        "matched": [],
        "error_code": code,
        "error_message": errors.message_for(code, detail),
    }


def query_inventory(**kwargs: Any) -> dict[str, Any]:
    summary = {
        "name_hint": kwargs.get("name_hint"),
        "product_id": kwargs.get("product_id"),
    }
    return with_invocation_log(
        tool="query_inventory",
        subject=auth.token_subject(),
        client_id=auth.token_client_id(),
        input_summary=summary,
        fn=lambda inv: _run_inventory(kwargs, inv),
    )


def _run_inventory(kwargs: dict[str, Any], inv: Any) -> dict[str, Any]:
    extras = set(kwargs) - {"name_hint", "product_id"}
    if extras:
        return _err(
            errors.INVENTORY_WRITE_FORBIDDEN,
            f"Unsupported fields: {', '.join(sorted(extras))}.",
        )
    if any(k in _WRITE_FIELDS for k in kwargs):
        return _err(errors.INVENTORY_WRITE_FORBIDDEN)

    try:
        inp = QueryInventoryInput.model_validate(kwargs)
    except ValidationError as exc:
        msg = str(exc)
        if "extra" in msg.lower() or any(f in msg for f in _WRITE_FIELDS):
            return _err(errors.INVENTORY_WRITE_FORBIDDEN, msg)
        return _err(errors.VALIDATION_ERROR, msg)
    except Exception as exc:
        return _err(errors.VALIDATION_ERROR, str(exc))

    scope_err = auth.require_scopes("inventory:read")
    if scope_err:
        return {**scope_err, "products": [], "matched": []}

    token = resolve_downstream_token(get_current_request())
    # Inventory GETs are public; token optional.
    try:
        if inp.product_id is not None:
            data = request_json(
                "GET",
                inventory_url(f"/api/v1/inventory/products/{inp.product_id}"),
                token=token,
            )
            products = [data] if isinstance(data, dict) else []
            matched = (
                match_products(products, inp.name_hint)
                if inp.name_hint
                else products
            )
            return {
                "ok": True,
                "products": products,
                "matched": matched,
                "error_code": None,
                "error_message": None,
            }

        products = request_json(
            "GET",
            inventory_url("/api/v1/inventory/products"),
            token=token,
        )
        if not isinstance(products, list):
            return _err(errors.UPSTREAM_ERROR, "Expected a product list.")
        matched = match_products(products, inp.name_hint)
        return {
            "ok": True,
            "products": products,
            "matched": matched,
            "error_code": None,
            "error_message": None,
        }
    except DownstreamError as exc:
        return _err(exc.code, exc.message if exc.code == errors.UPSTREAM_ERROR else None)


def register_inventory_tools(mcp: Any) -> None:
    @mcp.tool(
        name="query_inventory",
        description=(
            "Read-only lookup of inventory products and current stock. "
            "Write operations are not supported and will be rejected."
        ),
    )
    def _tool(
        name_hint: str | None = None,
        product_id: int | None = None,
    ) -> dict[str, Any]:
        return query_inventory(name_hint=name_hint, product_id=product_id)
