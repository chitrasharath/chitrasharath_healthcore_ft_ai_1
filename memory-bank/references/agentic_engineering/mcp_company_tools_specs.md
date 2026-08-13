# Spec — Company Tools MCP Server + Agent Migration (continuation of `feature/agent_tools_langgraph`)

> **Audience:** a coding agent building an MCP server and rewiring the existing LangGraph agent to use it.
> **Prerequisites:** Part 1 (`agent_rag_langgraph_specs.md`) and Part 2 (`agent_tools_incident_inventory_specs.md`) are implemented. The LangGraph agent lives in `services/api/app/domains/agent/` and today calls the incident/inventory HTTP API **directly** via `app/domains/agent/tools/{incident,inventory}.py`.
> **Reference solution:** `4GeeksAcademy/ai-engineering-syllabus` → `content/projects/ai-eng-mcp-company-tools/.learn/solution/README.md`. This spec follows its prescribed layout and error taxonomy.
> **Branch:** cut a new feature branch **`feature/agent_mcp_langgraph`** off `feature/agent_tools_langgraph`. Open the PR back into `feature/agent_tools_langgraph`.

---

## 1. Project overview

HealthCore is a FastAPI backend (`services/api`) with a LangGraph support agent that already routes between RAG (knowledge base) and two operational tools (incidents, inventory). Today those tools are **in-process Python functions** that call the backend's own HTTP API and forward the caller's bearer token.

This part extracts the operational tools into a **standalone MCP server** (`mcps/company-tools/`) built with **FastMCP**, protected by **OAuth 2.1 / OIDC bearer-JWT validation** implemented with the **[MCP Auth](https://mcp-auth.dev/) library (`mcpauth`)** — *not* FastMCP's built-in auth layer. The LangGraph agent then stops calling the API directly and instead **discovers and invokes the MCP tools via `langchain-mcp-adapters`**. The direct tool implementations are removed so there is a single code path to the operational data.

### Why this shape
- **Separation of concerns:** the MCP server is a reusable, auth-gated gateway to company operations that any MCP client (the agent, MCP Inspector, MCP Playground, future agents) can use.
- **Real auth:** every MCP request must present a valid OAuth 2.1/OIDC access token; unauthenticated or unauthorized calls are rejected *before* any tool executes, with documented error and exit codes.
- **Least privilege:** the inventory surface is **read-only by construction** — no write tool is exposed, and any write-shaped input is rejected before it reaches the backend.

### Behavioral contract (what "done" looks like)
- `mcps/company-tools/` runs as a **Streamable HTTP** MCP server that serves `/.well-known/oauth-protected-resource` (Protected Resource Metadata, RFC 9728) and returns **401 + `WWW-Authenticate`** on any unauthenticated tool list/call.
- A valid bearer JWT (correct `iss`, `aud`, signature verified against the provider's JWKS, and required scopes) unlocks two tools: `manage_incident_ticket` (create / update-status / get) and `query_inventory` (read-only).
- `query_inventory` **rejects any write** with `INVENTORY_WRITE_FORBIDDEN` before any HTTP call.
- Every tool invocation emits one **structured log line** (timestamp, client/subject, tool, input summary, result, duration).
- The LangGraph agent's `incident_tool` / `inventory_tool` nodes now go **through the MCP client** (`langchain-mcp-adapters`); the old `app/domains/agent/tools/{incident,inventory}.py` direct HTTP tools are **deleted**. RAG-vs-tool routing (Part 2) is behaviorally unchanged.
- Validated end-to-end in **MCP Playground / MCP Inspector**, with the flows and outcomes documented.

---

## 2. Locked design decisions (from clarifying questions)

1. **Auth library:** **`mcpauth`** (MCP Auth, <https://mcp-auth.dev/>). Do **not** use FastMCP's native OAuth/`BearerAuthProvider`. MCP Auth mounts Protected Resource Metadata and validates bearer JWTs against a compliant OIDC/OAuth 2.1 provider via its published JWKS.
2. **Transport:** **Streamable HTTP** (`streamable_http_app()`). Required so the server can expose `/.well-known/oauth-protected-resource` and issue `401 + WWW-Authenticate` challenges, and so MCP Inspector/Playground and `langchain-mcp-adapters`' `streamable_http` client can reach it. Justify this choice in the PR description (the reference solution asks for it).
3. **Downstream identity:** the MCP server **forwards the validated end-user access token** to the incidents/inventory HTTP API (consistent with Part 2). Per-user authorization is preserved end-to-end; inventory stays read-only regardless of the token's scopes. A service-account/token-exchange model is listed as a suggested hardening task (§14), not required now.
4. **Downstream data source:** MCP tools call the **live HTTP endpoints** of the services the student already built (`/api/v1/incidents*`, `/api/v1/inventory/products*`) — never mocked operational data inside the MCP process (reference-solution requirement).
5. **Provider / trust anchor:** **Keycloak**, self-hosted in `docker-compose` (realm `healthcore`), is the OAuth 2.1/OIDC Authorization Server. It supplies `issuer`, JWKS, `audience`, and scopes. The app's current local **HS256** tokens are *not* OIDC-compliant, so Keycloak is introduced for the MCP surface; the existing FastAPI login is untouched. Full realm/client/scope setup in **§4.5**.

---

## 3. Tech stack (delta)

Unchanged base: Python ≥3.12, `uv` workspace, FastAPI/Uvicorn, LangGraph, `httpx`, Pydantic. New in this part:

| Concern | Choice | Notes |
|---|---|---|
| MCP server framework | **FastMCP** | `FastMCP("company-tools")`; `.streamable_http_app()` for the Starlette ASGI app |
| MCP auth | **`mcpauth`** (MCP Auth) | Protected Resource Metadata + bearer JWT middleware; deps: `pydantic`, `pyjwt[crypto]`, `requests`, `starlette` |
| Agent ↔ MCP | **`langchain-mcp-adapters`** | `MultiServerMCPClient` → LangChain tools loaded into the graph |
| Downstream HTTP | **`httpx`** (already present) | explicit timeouts on every downstream call |
| OIDC provider | see §4 | issuer/JWKS/audience/scopes |

The MCP server is a **separate package under `mcps/`**, not under `services/`. It is a workspace member so `uv` manages it (§12).

---

## 4. Auth model (`mcpauth`, least privilege) — the core requirement

### 4.1 Trust anchor
The MCP server is an OAuth **resource server**. On startup it fetches the authorization server's metadata from the configured issuer and uses the provider's **JWKS** to verify token signatures. Nothing is validated with the app's local `secret_key`.

Required config (env, §12):
- `OIDC_ISSUER` — issuer URL (its `/.well-known/openid-configuration` or `/.well-known/oauth-authorization-server` is fetched).
- `OIDC_AUDIENCE` — expected `aud` claim (this resource server's identifier).
- `OIDC_RESOURCE` — the protected-resource identifier advertised in Protected Resource Metadata (the canonical MCP server URL).
- `MCP_REQUIRED_SCOPES` — space-separated scopes required to invoke tools (least privilege; see §4.4).

> **Confirm the provider first** (§16). Options considered: Keycloak self-hosted in `docker-compose` (offline, most faithful for grading), a hosted dev tenant (Auth0/Okta/Entra), or upgrading the app's own auth to RS256+JWKS to act as the AS. Whichever is chosen, it must publish OIDC discovery + JWKS, and mint tokens with the `aud` and scopes below.

### 4.2 `auth.py` — MCP Auth wiring (do NOT use FastMCP built-in auth)
```python
# mcps/company-tools/auth.py
from __future__ import annotations
import os
from mcpauth import MCPAuth
from mcpauth.config import AuthServerType, ResourceServerConfig, ResourceServerMetadata
from mcpauth.utils import fetch_server_config

# 1) Discover the authorization server (OIDC discovery -> issuer, jwks_uri, etc.)
auth_server_config = fetch_server_config(os.environ["OIDC_ISSUER"], AuthServerType.OIDC)

# 2) Declare THIS server as a protected resource (RFC 9728 metadata)
mcp_auth = MCPAuth(
    protected_resources=ResourceServerConfig(
        metadata=ResourceServerMetadata(
            resource=os.environ["OIDC_RESOURCE"],
            authorization_servers=[auth_server_config],
            scopes_supported=["incidents:read", "incidents:write", "inventory:read"],
        )
    )
)

REQUIRED_SCOPES = os.environ.get("MCP_REQUIRED_SCOPES", "").split()

# 3) Bearer JWT validation middleware — 'jwt' mode verifies signature via JWKS,
#    checks iss/aud/exp and required scopes on every request.
bearer_middleware = mcp_auth.bearer_auth_middleware(
    "jwt",
    audience=os.environ["OIDC_AUDIENCE"],
    resource=os.environ["OIDC_RESOURCE"],
    required_scopes=REQUIRED_SCOPES,
)
```
> Identifier names (`MCPAuth`, `fetch_server_config`, `bearer_auth_middleware`, `ResourceServerConfig`, `ResourceServerMetadata`, `AuthServerType`) follow the MCP Auth Python SDK (`mcpauth` ≥0.1.1). **Pin to the installed version and adjust to its exact signatures** — verify against `mcp-auth.dev/docs` and the installed package after `uv add mcpauth`.

### 4.3 Mounting metadata + middleware on the Streamable HTTP app
```python
# mcps/company-tools/main.py (sketch)
from starlette.applications import Starlette
from starlette.routing import Mount
from mcp.server.fastmcp import FastMCP
from auth import mcp_auth, bearer_middleware
from tools.incidents import register_incident_tools
from tools.inventory import register_inventory_tools

mcp = FastMCP("company-tools")
register_incident_tools(mcp)
register_inventory_tools(mcp)

app = Starlette(
    routes=[
        mcp_auth.metadata_route(),          # serves /.well-known/oauth-protected-resource
        Mount("/", app=mcp.streamable_http_app(), middleware=[bearer_middleware]),
    ]
)
```
- Unauthenticated request → **HTTP 401** with `WWW-Authenticate: Bearer resource_metadata="…/.well-known/oauth-protected-resource"` (points the client at discovery). The tool list and every tool call sit **behind** the middleware.
- The exact `metadata_route()` / middleware-attachment API must match the installed `mcpauth` + FastMCP versions; the requirement is: **PRM served, bearer validated on tool list and tool call, framework built-in auth unused.**

### 4.4 Principle of least privilege
- **Scopes:** `manage_incident_ticket` requires `incidents:read` for `get`, `incidents:write` for `create`/`update_status`; `query_inventory` requires only `inventory:read`. Enforce per-action inside the tool (check the validated token's scopes) in addition to the coarse `MCP_REQUIRED_SCOPES` gate. A token with only `inventory:read` must not be able to create incidents.
- **No inventory writes exist at all** — least privilege by omission (§6.2).
- **Downstream:** forward only the user's token; never attach ambient admin credentials. Never log the token.
- **Redaction:** reuse the repo's PII redaction (`app.domains.knowledge.pii.redact_pii`) if incident payloads are logged.

### 4.5 OIDC provider — **Keycloak** (self-hosted in docker-compose)

**Decision:** the trust anchor is a **Keycloak** realm run in `docker-compose`. Rationale: it's a fully OAuth 2.1 / OIDC-compliant Authorization Server, runs offline (no external tenant/account, works in Codespaces and CI, gradable deterministically), publishes real OIDC discovery + JWKS, and mints RS256 tokens with `iss`/`aud`/`exp`/scopes — exactly what `mcpauth` validates against. This replaces the app's non-compliant local HS256 tokens *for the MCP surface* (the existing FastAPI login is untouched; only the MCP server and the tokens the agent presents to it move to Keycloak).

#### 4.5.1 docker-compose service (dev)
Add to `docker-compose.yml`:
```yaml
  keycloak:
    image: quay.io/keycloak/keycloak:26.0
    command: ["start-dev", "--import-realm"]
    environment:
      KC_BOOTSTRAP_ADMIN_USERNAME: admin
      KC_BOOTSTRAP_ADMIN_PASSWORD: admin      # dev only — never in prod
      KC_HTTP_PORT: 8080
    ports:
      - "8080:8080"
    volumes:
      - ./mcps/company-tools/keycloak/realm-export.json:/opt/keycloak/data/import/realm-export.json:ro
```
The realm is provisioned declaratively via the imported `realm-export.json` so `docker compose up` yields a ready-to-use provider with zero manual clicks (commit the export; it contains no real secrets).

#### 4.5.2 Realm / client / scopes to provision
Realm **`healthcore`** (issuer becomes `http://localhost:8080/realms/healthcore`):

| Object | Value | Purpose |
|---|---|---|
| **Client scopes** | `incidents:read`, `incidents:write`, `inventory:read` | the least-privilege scopes enforced in §4.4 |
| **API audience** | client/mapper adds `aud = company-tools-mcp` | the `OIDC_AUDIENCE` the resource server checks |
| **Agent client** | `agent-support` (confidential, `client_credentials` **and** `password` grants enabled for dev) | how the LangGraph agent / MCP Inspector obtains a token |
| **Test user** | `coordinator` / password, granted all three scopes | interactive/"password grant" flows in MCP Playground |
| **Restricted user** | `readonly` , granted only `inventory:read` + `incidents:read` | proves `AUTH_INSUFFICIENT_SCOPE` on `create` |

Add a **protocol mapper** (audience mapper) on the `agent-support` client so issued access tokens carry `aud: company-tools-mcp`, and an **Audience/scope mapper** so requested scopes land in the token's `scope` claim (Keycloak emits scopes space-delimited in `scope`; `mcpauth` reads them for `required_scopes`).

#### 4.5.3 Resulting env values
```
OIDC_ISSUER=http://localhost:8080/realms/healthcore
OIDC_AUDIENCE=company-tools-mcp
OIDC_RESOURCE=http://localhost:9000/mcp          # canonical MCP URL advertised in PRM
MCP_REQUIRED_SCOPES=inventory:read               # coarse gate; per-action scopes checked in-tool (§4.4)
```
> In Docker networking the MCP server reaches Keycloak at `http://keycloak:8080/...`; MCP Inspector/Playground and the browser use `http://localhost:8080/...`. If issuer host differs between token-minting and validation, set Keycloak's `KC_HOSTNAME`/frontend-URL so the `iss` claim matches `OIDC_ISSUER` exactly — a mismatch is the most common `AUTH_INVALID_TOKEN` cause.

#### 4.5.4 Minting a test token (for MCP Inspector / Playground / curl)
```bash
# Password grant for the interactive test user (dev only)
curl -s -X POST http://localhost:8080/realms/healthcore/protocol/openid-connect/token \
  -d grant_type=password \
  -d client_id=agent-support -d client_secret=<dev-secret> \
  -d username=coordinator -d password=<pw> \
  -d scope="openid incidents:read incidents:write inventory:read" \
  | jq -r .access_token
```
Paste the resulting JWT as the bearer token in MCP Inspector/Playground. For the restricted-scope test, mint with `username=readonly` and request only `inventory:read incidents:read`.

---

## 5. Directory layout (reference-solution prescribed)

```
mcps/
  company-tools/
    __init__.py
    main.py            # FastMCP app + Starlette mount + PRM + bearer middleware
    auth.py            # mcpauth wiring (§4)
    config.py          # env-driven settings (issuer, audience, resource, base URLs, timeout)
    logging.py         # structured per-invocation logger (§7)
    downstream.py      # httpx helpers to call incidents/inventory API (timeouts, error mapping)
    errors.py          # error codes + exit codes (§8)
    tools/
      __init__.py
      incidents.py     # manage_incident_ticket
      inventory.py     # query_inventory (read-only)
    keycloak/
      realm-export.json  # healthcore realm: clients, scopes, mappers, test users (§4.5)
    README.md          # run + validation docs (§10, §11)
    tests/
      test_auth.py
      test_tools.py
```
> `mcps/` sits at the repo root, a sibling of `services/`. "All MCP servers for the company live here — not under `services/`."

---

## 6. Tool contracts (name, description, I/O schema)

Both tools are registered on the FastMCP instance with explicit typed input/output (Pydantic / typed signatures so FastMCP publishes a JSON Schema for discovery). **Tools never raise raw exceptions to the transport** — on any failure they return a structured error object with a documented code (§8).

### 6.1 `manage_incident_ticket`
- **Name:** `manage_incident_ticket`
- **Description:** `"Create, update status, or get an incident ticket in the HealthCore Incident Manager. Requires a valid OAuth access token with the appropriate incidents scope."`
- **Input schema:**
  ```python
  class ManageIncidentInput(BaseModel):
      action: Literal["create", "update_status", "get"]
      ticket_id: int | None = None       # required for update_status / get
      status: str | None = None          # required for update_status
      # create fields (all optional per IncidentCreate):
      title: str | None = None
      description: str | None = None
      category: str | None = None
      origin: str | None = None
      branch: str | None = None
  ```
  Cross-field rules (return `VALIDATION_ERROR` with field detail on violation):
  - `create` → ignores `ticket_id`/`status`; sends `IncidentCreate` fields.
  - `update_status` → requires `ticket_id` **and** `status`.
  - `get` → requires `ticket_id`.
- **Output schema:**
  ```python
  class IncidentToolOutput(BaseModel):
      ok: bool
      incident: dict | None = None       # IncidentRead on success
      error_code: str | None = None      # §8
      error_message: str | None = None
  ```
- **Downstream HTTP** (base `INCIDENTS_API_BASE_URL`, default the internal API):
  - `create` → `POST /api/v1/incidents` (201 → `IncidentRead`).
  - `update_status` → `PATCH /api/v1/incidents/{ticket_id}/status` body `{"status": <status>}` (200 → `IncidentRead`; 404 → `not_found`).
  - `get` → `GET /api/v1/incidents/{ticket_id}` (200 → `IncidentRead`; 404 → `not_found`).
  - Header `Authorization: Bearer <forwarded user token>`; explicit `httpx.Timeout`.
  - Scope check: `get` needs `incidents:read`; `create`/`update_status` need `incidents:write` → else `AUTH_INSUFFICIENT_SCOPE`.

### 6.2 `query_inventory` (read-only)
- **Name:** `query_inventory`
- **Description:** `"Read-only lookup of inventory products and current stock. Write operations are not supported and will be rejected."`
- **Input schema:**
  ```python
  class QueryInventoryInput(BaseModel):
      name_hint: str | None = None       # case-insensitive match on name/sku
      product_id: int | None = None      # optional direct lookup
      # Any write-shaped field (e.g. 'quantity', 'delta', 'set_stock') -> reject.
  ```
- **Output schema:**
  ```python
  class InventoryToolOutput(BaseModel):
      ok: bool
      products: list[dict] = []           # MedicalSupplyRead[]
      matched: list[dict] = []            # subset matching name_hint
      error_code: str | None = None
      error_message: str | None = None
  ```
- **Downstream HTTP:** `GET /api/v1/inventory/products` (returns all; filter `matched` in-tool by case-insensitive substring on `name`/`sku`), or `GET /api/v1/inventory/products/{product_id}` when `product_id` set. Requires `inventory:read`.
- **Write rejection:** the tool exposes **no** create/update/delete action. If the input carries any write-shaped field, or a mutating action is requested by any means, return **`INVENTORY_WRITE_FORBIDDEN`** with message `"Inventory tool is read-only. Write operations are not permitted on this MCP server."` **before** any HTTP call. No inventory write tool is registered on the MCP server at all.

> Reuse the existing in-tool matching logic from Part 2's `tools/inventory.py` (`_match_products`, token/plural handling) when implementing `query_inventory` — port it into the MCP server, then delete the old module (§9).

---

## 7. Logging — every tool invocation

`logging.py` provides a structured logger; each tool wraps its body so that **exactly one** structured record is emitted per call (success or failure):
```json
{
  "timestamp": "2026-07-27T12:00:00Z",
  "subject": "<sub claim from validated JWT>",
  "client_id": "<azp/client_id claim, if present>",
  "tool": "manage_incident_ticket",
  "input_summary": {"action": "get", "ticket_id": 482},
  "result": "success",           // success | error
  "error_code": null,             // §8 code when result=error
  "duration_ms": 145
}
```
Rules:
- **Never** log the bearer token, full incident `description`, or PII — summarize inputs (ids, action, name_hint) and `redact_pii` any free text if included.
- Log auth rejections too (missing/invalid token, insufficient scope, write-forbidden) with the code — but without the token value.
- Emit via the standard `logging` module (JSON formatter) so it composes with the existing backend logging.

---

## 8. Error codes & exit codes (documented — required)

### 8.1 Tool / request error codes (returned in output or as the auth challenge)
| Scenario | `error_code` | HTTP-equivalent | Behavior |
|---|---|---|---|
| No bearer token presented | `AUTH_MISSING_TOKEN` | 401 | Reject before tool list/invoke; `WWW-Authenticate` challenge |
| Invalid signature / expired / bad `iss`/`aud` | `AUTH_INVALID_TOKEN` | 401 | Reject before invoke |
| Token valid but missing required scope | `AUTH_INSUFFICIENT_SCOPE` | 403 | Reject before downstream call |
| Inventory write attempted | `INVENTORY_WRITE_FORBIDDEN` | 403 | Reject before any HTTP call |
| Bad/missing tool input (field rules) | `VALIDATION_ERROR` | 422 | Field-level detail |
| Incident id not found downstream | `NOT_FOUND` | 404 | From downstream 404 |
| Downstream timeout | `UPSTREAM_TIMEOUT` | 504 | Explicit timeout hit |
| Downstream 5xx / transport error | `UPSTREAM_ERROR` | 502 | Includes original status when known |
Each code has a **documented, specific message** (no generic "error"). Auth rejections (401/403) are enforced by the `mcpauth` bearer middleware and/or per-action scope checks; the rest are returned as structured tool outputs.

### 8.2 Process exit codes (server startup / lifecycle)
| Exit code | Meaning |
|---|---|
| `0` | Clean shutdown |
| `1` | Unhandled fatal error |
| `78` | **Config error** (`EX_CONFIG`) — missing/invalid `OIDC_ISSUER`, `OIDC_AUDIENCE`, `OIDC_RESOURCE`, or base URLs |
| `69` | **Unavailable** (`EX_UNAVAILABLE`) — cannot reach the OIDC issuer / fetch JWKS at startup |
Validate all required env on startup and `sys.exit(78)` with a clear message if any are missing; `sys.exit(69)` if `fetch_server_config` cannot reach the provider. Document these in `mcps/company-tools/README.md`.

---

## 9. Agent migration to MCP (`langchain-mcp-adapters`) — remove direct tools

### 9.1 New MCP client seam in the agent package
Add `services/api/app/domains/agent/mcp_client.py`:
```python
from langchain_mcp_adapters.client import MultiServerMCPClient

def build_mcp_client() -> MultiServerMCPClient:
    return MultiServerMCPClient({
        "company-tools": {
            "url": settings.mcp_company_tools_url,     # e.g. http://localhost:9000/mcp
            "transport": "streamable_http",
            # bearer token injected per-invocation from graph state (see 9.2)
        }
    })
# load_mcp_tools(session) -> list[BaseTool]; cache the loaded tools at import.
```

### 9.2 Rewire the tool nodes
- `incident_tool_node` and `inventory_tool_node` (in `nodes.py`) stop importing `run_incident_tool` / `run_inventory_tool`. Instead they call the MCP tools (`manage_incident_ticket`, `query_inventory`) through the adapter, passing the **caller's bearer token** (already threaded into `state["auth_token"]` in Part 2) as the `Authorization` header on the MCP request.
- Map the classifier's `intent` (`incident_id`, `product_hint`) to the MCP tool inputs (`action="get"`/`ticket_id`, `name_hint`).
- Preserve the Part 2 recovery contract: MCP errors (auth, timeout, upstream) map to `ok=False`/`empty` in `incident_result`/`inventory_result` so `after_gather` → `honest_fallback` / deterministic §6 fallback lines still fire. **Nodes must not raise into the graph.**
- Keep `sources_used += ["incident_tool"|"inventory_tool"]` and the per-node trace steps unchanged so existing evals keep asserting against the trace.

### 9.3 Remove the direct implementations
- **Delete** `app/domains/agent/tools/incident.py` and `app/domains/agent/tools/inventory.py` and their exports in `tools/__init__.py`. Keep `tools/base.py` only if still used elsewhere; otherwise remove it too. There must be **one path** to operational data — through the MCP server.
- Remove now-dead settings if unused (`internal_api_base_url` may still be used by the MCP server's `downstream.py`, but the agent no longer needs it).

### 9.4 Confirm routing still works
- RAG-only questions still resolve via `retrieve → compose` (no MCP call).
- Incident/inventory questions resolve via the MCP tool nodes.
- "Both" questions still fan out to RAG + MCP inventory.
- Update the Part 2 evals only where the tool call site changed: stub the **MCP client** (or the loaded MCP tool callables) instead of the old `run_*_tool` HTTP stubs; assertions remain against `sources_used` / `trace_steps`. Existing RAG tests (`tests/pipelines/test_rag.py`, `services/api/tests/test_knowledge.py`) must stay green.

---

## 10. Validation in MCP Playground / Inspector (test + document)

The server binds to `localhost`, which public playgrounds can't reach, so expose it first:
1. Run the server (`uv run` — §11). In **GitHub Codespaces**, forward the MCP port with **public** visibility; copy the forwarded HTTPS URL. (Locally, MCP Inspector `npx @modelcontextprotocol/inspector` can reach `localhost` directly.)
2. Point **MCP Playground** (<https://www.mcpplayground.tech/playground>) or **MCP Inspector** at the forwarded `…/mcp` URL with a valid OAuth access token.
3. Validate and **document (screenshots + notes in `mcps/company-tools/README.md`)**:
   - **Discovery:** tool list returns both tools with their input/output schemas; `/.well-known/oauth-protected-resource` resolves.
   - **Unauthenticated:** a call with no/invalid token is rejected with `AUTH_MISSING_TOKEN` / `AUTH_INVALID_TOKEN` (401 + `WWW-Authenticate`).
   - **Incident flow:** `create` → `update_status` → `get` round-trips against the live API.
   - **Inventory read:** `query_inventory` returns products/matched.
   - **Write rejection:** an inventory write-shaped call returns `INVENTORY_WRITE_FORBIDDEN`.
   - **Insufficient scope:** an `incidents:read`-only token calling `create` returns `AUTH_INSUFFICIENT_SCOPE`.
4. **Agent end-to-end:** run the LangGraph agent with a valid token; confirm incident/inventory questions now flow through the MCP client node and RAG routing is unchanged.

Also add automated tests (`mcps/company-tools/tests/`): auth middleware rejects unauthenticated (401), scope enforcement, `INVENTORY_WRITE_FORBIDDEN`, and `VALIDATION_ERROR` on bad input — mocking downstream `httpx` (e.g. `respx`) and the JWKS/verification so tests run offline.

---

## 11. Development workflow

```bash
git fetch origin
git checkout -b feature/agent_mcp_langgraph origin/feature/agent_tools_langgraph

# 1) Add the MCP server as a workspace member + deps
uv add --package company-tools mcpauth fastmcp        # in mcps/company-tools/pyproject.toml
uv add --package healthcore-api langchain-mcp-adapters # agent side
uv sync

# 2) Bring up Keycloak (imports realm-export.json) and mint a test token (§4.5)
docker compose up -d keycloak                              # issuer at :8080/realms/healthcore
#    then curl the token endpoint (§4.5.4) for user 'coordinator' -> access_token JWT

# 3) Run the backend API (tools call it downstream) and the MCP server
uv run uvicorn app.main:app --reload                      # services/api  (:8000)
uv run python -m mcps.company_tools.main                  # MCP server    (:9000, streamable-http)

# 4) Validate in MCP Inspector / Playground (§10)
npx @modelcontextprotocol/inspector                        # point at http://localhost:9000/mcp + token

# 5) Guardrails + migrated evals
uv run pytest tests/pipelines/test_rag.py services/api/tests/test_knowledge.py -q  # stay green
uv run pytest tests/pipelines/test_agent_evals.py -q                                # MCP-stubbed
uv run pytest mcps/company-tools/tests -q                                           # new MCP tests
```
Commit granularly: (a) MCP scaffold + auth, (b) incident tool, (c) inventory tool + write-rejection, (d) logging + error/exit codes, (e) agent migration + delete direct tools, (f) tests + validation docs.

---

## 12. Dependencies & environment

**New packages:**
- `mcps/company-tools`: `mcpauth`, `fastmcp` (pulls `mcp`, `starlette`, `pydantic`, `pyjwt[crypto]`, `httpx`, `requests`).
- `services/api` (agent side): `langchain-mcp-adapters`.
- Dev/test: `respx` (mock httpx), `pytest`.

**Workspace:** add `mcps/company-tools` to the root `pyproject.toml` `[tool.uv.workspace].members` and give it its own `pyproject.toml` (name `company-tools`, `requires-python >=3.12`).

**New env keys** (document in `.example.env` and `mcps/company-tools/README.md`):
```
# OIDC / OAuth 2.1 provider (Keycloak, realm 'healthcore' — §4.5)
OIDC_ISSUER=http://localhost:8080/realms/healthcore   # http://keycloak:8080/... inside Docker
OIDC_AUDIENCE=company-tools-mcp
OIDC_RESOURCE=http://localhost:9000/mcp   # canonical MCP server URL / resource id
MCP_REQUIRED_SCOPES=inventory:read        # coarse gate; per-action scopes checked in-tool (§4.4)
# MCP server
MCP_HOST=0.0.0.0
MCP_PORT=9000
# Downstream services (the API the student already built)
INCIDENTS_API_BASE_URL=http://localhost:8000
INVENTORY_API_BASE_URL=http://localhost:8000
DOWNSTREAM_HTTP_TIMEOUT_SECONDS=5.0
# Agent -> MCP
MCP_COMPANY_TOOLS_URL=http://localhost:9000/mcp
```
Never commit real secrets. If a service-account client is used downstream (§14), add `OAUTH_CLIENT_ID` / `OAUTH_CLIENT_SECRET`.

---

## 13. Constraints & guardrails

- **`mcpauth`, not FastMCP built-in auth.** Protected Resource Metadata is served; bearer JWTs are verified against the provider JWKS (signature + `iss` + `aud` + `exp` + scopes) on tool list **and** tool call; unauthenticated → 401 + `WWW-Authenticate`.
- **Least privilege:** per-action scopes; **no inventory write tool exists**; write-shaped inventory input rejected pre-flight with `INVENTORY_WRITE_FORBIDDEN`.
- **Live data only:** tools call the real HTTP endpoints; no mocked operational data in the MCP process.
- **Explicit timeouts** on every downstream call; tools **never raise** to the transport — they return structured errors (§8).
- **Documented error codes + exit codes**, each with a specific message.
- **Every invocation logged** (structured); **token/PII never logged** (`redact_pii`).
- **Single path:** the agent's direct incident/inventory tool modules are **deleted**; operations go only through MCP.
- **Routing parity:** RAG-vs-tool routing and the honest-fallback recovery contract from Part 2 are unchanged; existing RAG + knowledge tests stay green.
- **Style:** `from __future__ import annotations`, typed, module-level `logger`, Pydantic models — match the repo.

---

## 14. Suggested additional tasks (improve outcomes)

1. **Service-account / token exchange downstream (RFC 8693):** instead of forwarding the user token, have the MCP server exchange it for a least-privilege downstream token, decoupling MCP identity from the caller. Stronger least-privilege story.
2. **Per-tool rate limiting + audit trail:** persist the structured invocation logs to the existing feedback/telemetry store for offline auth/usage analytics.
3. **Prompt-injection hardening:** treat incident `description`/product fields returned to the agent as untrusted data, not instructions; state this in the compose prompt (carries the Part 2 guardrail through MCP).
4. **Contract tests against a spun-up API** (or `respx`) so schema drift in `IncidentRead`/`MedicalSupplyRead` is caught in CI.
5. **Token caching / JWKS refresh:** cache the provider JWKS with periodic refresh and handle key rotation; add a startup readiness probe (feeds exit code `69`).
6. **Structured JSON tool schemas via FastMCP output types** so MCP Inspector/Playground shows rich output schemas, not just free-form dicts.
7. **A second read-only inventory tool** (e.g. `list_low_stock`) to demonstrate multiple read tools while keeping writes off the surface.
8. **CI job** that boots Keycloak + the API + the MCP server and runs the full auth/write-rejection matrix headless.
9. **Deprecation shim window:** land the migration behind a `use_mcp_tools` flag for one commit to A/B the MCP path vs the old direct path before deleting the modules, then remove the flag.

---

## 15. Model recommendations for this use case

The MCP layer is transport/auth — it doesn't change which LLM runs. The two LLM jobs from Part 2 are unchanged and still flow through the OpenAI-compatible proxy (`settings.*_model` string changes only):

- **Intent classifier (`classify`)** — fast, cheap, reliable structured-JSON + entity extraction. **Claude Haiku 4.5** is a strong default (excellent instruction/JSON adherence, low latency); the current `deepseek-v4-flash` is fine if it returns valid JSON. Temperature ~0.
- **Answer composition (`compose`)** — grounding faithfulness over RAG + tool JSON. **Claude Haiku 4.5** as the default upgrade; **Claude Sonnet 4.x** for the quality tier on blended "both" answers (policy + live data, US/UK splits).
- **If you move the agent to native tool-calling to consume MCP tools directly** (instead of the fixed classifier→node fan-out), prefer a model with first-class function-calling — **Claude Sonnet 4.x** — and confirm the 4Geeks proxy exposes tool-calling for it before committing (deepseek tool-calling through the proxy is unverified).
- **Do not change the embedding model** (`pplx-embed-v1`) — retrieval vectors are coupled to it.

---

## 16. Assumptions & open items

- **OIDC provider = Keycloak** (realm `healthcore`) in `docker-compose`, chosen for an offline, gradable, standards-compliant AS. Full setup in §4.5. The existing FastAPI HS256 login is untouched; Keycloak governs only the MCP surface. — *confirmed.*
- **Scopes** `incidents:read`, `incidents:write`, `inventory:read` are provisioned as Keycloak client scopes (§4.5.2); align final names with `CONTEXT-company.md` if it dictates otherwise. — *confirm against context doc.*
- **Keycloak issuer host** must match the token's `iss` exactly across Docker/localhost boundaries (set `KC_HOSTNAME`/frontend URL); a mismatch is the most common `AUTH_INVALID_TOKEN` cause (§4.5.3). — *watch during integration.*
- **Transport = Streamable HTTP**, chosen so PRM/`WWW-Authenticate` work and MCP Playground can reach the server; justify in the PR. — *confirmed.*
- **Downstream identity = forward the user's validated token** (Part 2 behavior). Service-account/token-exchange is a hardening follow-up (§14.1). — *confirmed direction.*
- **`mcpauth` Python SDK identifiers** (`MCPAuth`, `fetch_server_config`, `bearer_auth_middleware`, `ResourceServerConfig`, `ResourceServerMetadata`, `AuthServerType`) are per the current SDK; **pin to the installed version and adjust signatures** to match `mcp-auth.dev/docs`. — *verify against installed package.*
- **Downstream base URL** defaults to the internal API (`http://localhost:8000`); in Docker/compose set `INCIDENTS_API_BASE_URL` / `INVENTORY_API_BASE_URL` to the API service URL. — *confirm deployed base.*
- **MCP Playground vs Inspector:** the reference uses MCP Playground (needs a public/forwarded URL); MCP Inspector is the local-friendly equivalent. Either satisfies "validate in MCP Playground" — document whichever you use. — *confirmed.*

---

## 17. Acceptance / validation checklist

- [ ] Work on `feature/agent_mcp_langgraph`, branched off `feature/agent_tools_langgraph`.
- [ ] `mcps/company-tools/` MCP server (FastMCP, Streamable HTTP) under `mcps/`, not `services/`.
- [ ] **Keycloak** (realm `healthcore`) runs in docker-compose via committed `realm-export.json`, minting RS256 tokens with `aud=company-tools-mcp` and the three scopes; test users `coordinator` (all scopes) and `readonly` (read-only) exist (§4.5).
- [ ] `mcpauth` mounts Protected Resource Metadata and validates bearer JWTs against Keycloak's JWKS (iss/aud/exp/scopes); FastMCP built-in auth **not** used.
- [ ] Unauthenticated tool list/call rejected with 401 + `WWW-Authenticate` (`AUTH_MISSING_TOKEN` / `AUTH_INVALID_TOKEN`).
- [ ] Least privilege: per-action scopes enforced; **no inventory write tool**; write-shaped input → `INVENTORY_WRITE_FORBIDDEN` pre-flight.
- [ ] `manage_incident_ticket` (create / update_status via `PATCH /api/incidents/{id}/status` / get) and `query_inventory` (read-only) documented with name, description, input/output schema.
- [ ] Every tool invocation emits one structured log line (no token/PII).
- [ ] Error codes **and** process exit codes documented with specific messages (§8).
- [ ] Validated in MCP Playground/Inspector; discovery, auth reject, incident round-trip, inventory read, write rejection, insufficient scope all captured in `mcps/company-tools/README.md`.
- [ ] Agent migrated to MCP via `langchain-mcp-adapters`; `tools/incident.py` + `tools/inventory.py` **deleted**; single path to operational data.
- [ ] RAG-vs-tool routing unchanged; honest-fallback recovery preserved; RAG + knowledge tests green; agent evals updated to stub the MCP client and still assert against the trace.
- [ ] New deps + workspace member + `.example.env` keys committed; no secrets in code/logs.
```
