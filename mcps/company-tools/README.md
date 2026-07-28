# Company Tools MCP Server

Streamable HTTP MCP gateway for HealthCore **incidents** and **inventory**, protected by **mcpauth** + **Keycloak** (OIDC).

> **Dev only** credentials (never use in prod):
>
> | Thing | Value |
> |-------|--------|
> | Keycloak admin | `http://localhost:8080` → `admin` / `admin` |
> | OAuth client | `agent-support` / secret `agent-support-dev-secret` |
> | Full-scope user | `coordinator` / `coordinator` (request `incidents:write`) |
> | Read-only user | `readonly` / `readonly` (no write scope) |
> | Smoke API user | `mcp-smoke@example.com` / `password123` (register once) |

---

## Concepts (read once)

### Why two tokens?

| Token | Issuer | Header | Purpose |
|-------|--------|--------|---------|
| `$KC_TOKEN` | Keycloak `:8080` | `Authorization: Bearer …` | Proves you may call the **MCP server** |
| `$API_TOKEN` | FastAPI `:8000` login | `X-Downstream-Authorization: Bearer …` | Proves you may call **incidents** on the API |

They are not interchangeable. Inventory GETs are public, so inventory often works with only `$KC_TOKEN`. Incidents need **both**.

### Ports

| Port | Service |
|------|---------|
| **8080** | Keycloak (OIDC) |
| **8000** | FastAPI HealthCore API |
| **9000** | company-tools MCP |

### How we validate (Inspector)

`npx @modelcontextprotocol/inspector` (v2) has **no** classic connection form for headers. Use the **CLI**:

```bash
npx @modelcontextprotocol/inspector --cli \
  http://localhost:9000/mcp \
  --transport http \
  --method tools/list \
  --header "Authorization: Bearer $KC_TOKEN"
```

Do **not** use OAuth / Dynamic Client Registration in the web UI for this milestone.

### Valid incident enums (API rejects others with HTTP 400)

| Field | Valid values |
|-------|----------------|
| `category` | `APPOINTMENT`, `BILLING`, `CLINICAL_CARE`, `ACCESSIBILITY`, `ADMINISTRATIVE` |
| `origin` | `customer`, `branch`, `internal` |
| `branch` | clinic codes e.g. `US-TX-01`, or `Central` |
| `status` (updates) | `open` → `in_progress` → `resolved` / `discarded` |

### Token lifetimes

- Keycloak access tokens expire in **~5 minutes** — remint before each block of CLI calls if unsure.
- FastAPI JWT lasts `JWT_EXPIRE_MINUTES` (often 15–30). Remint if incidents return HTTP 401.

---

# Manual testing guide

Use **4 terminals**. Keep tokens in **Terminal D** only (same shell).

| Terminal | Role |
|----------|------|
| A | Keycloak |
| B | FastAPI `:8000` |
| C | MCP `:9000` |
| D | curls / tokens / Inspector CLI / pytest |

---

## Step 0 — Prerequisites

From repo root:

1. Docker, `uv`, `jq`, `npx` available.
2. Root `.env` has MCP/OIDC keys (from `.example.env`), **or** you will export them in Step 3.
3. `services/api/.env` has `SECRET_KEY`, `JWT_EXPIRE_MINUTES`, and for agent tests: `LLM_API_KEY`, `MCP_COMPANY_TOOLS_URL`, `KEYCLOAK_*`.

---

## Step 1 — Start Keycloak (Terminal A)

**What this does:** Boots the OIDC provider that mints RS256 JWTs and publishes JWKS for MCP to verify.

```bash
cd /workspaces/chitrasharath_healthcore_ft_ai_1
docker compose up -d keycloak
```

Wait until ready (often 30–90s on first boot / after recreate):

```bash
# Terminal D — retry until you see 200
curl -s -o /dev/null -w "%{http_code}\n" \
  http://localhost:8080/realms/healthcore/.well-known/openid-configuration
```

**Pass:** `200`.  
**Fail:** `000` → Keycloak still starting; wait and retry. **Do not start MCP yet.**

---

## Step 2 — Start the API (Terminal B)

**What this does:** Runs the live incidents/inventory HTTP APIs that MCP calls downstream.

```bash
cd /workspaces/chitrasharath_healthcore_ft_ai_1/services/api
uv run uvicorn app.main:app --reload --port 8000
```

Wait for `Application startup complete`, then verify:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/docs
```

**Pass:** `200`. Leave Terminal B running.

If inventory/incident MCP calls return `UPSTREAM_ERROR` with connection errors, this process is down.

---

## Step 3 — Start the MCP server (Terminal C)

**What this does:** Starts FastMCP Streamable HTTP on `:9000`, loads Keycloak JWKS at startup, mounts PRM + bearer auth.

From **repo root** (so pydantic can read root `.env`):

```bash
cd /workspaces/chitrasharath_healthcore_ft_ai_1
uv run company-tools
```

Exports are **optional** if root `.env` already has `OIDC_*`, `MCP_*`, `INCIDENTS_API_BASE_URL`, `INVENTORY_API_BASE_URL`.

**Pass:** log `Starting company-tools MCP on 0.0.0.0:9000` and no immediate exit.

| Exit | Meaning |
|------|---------|
| **69** | Keycloak not reachable — finish Step 1 (`200`), then retry |
| **78** | Missing required env |
| **Address already in use** | Old MCP still on `:9000` — that is OK; use the existing one |

Verify PRM:

```bash
curl -s http://localhost:9000/.well-known/oauth-protected-resource | jq .
```

**Pass:** JSON with `resource`, `authorization_servers`, `scopes_supported`.

---

## Step 4 — Mint tokens (Terminal D)

**What this does:** Saves JWTs in shell variables for the rest of the session.

Stay in **one** shell.

### 4a. Keycloak full-scope token (`$KC_TOKEN`)

**What:** Password grant as `coordinator`, requesting read+write scopes. Used for MCP `Authorization`.

```bash
KC_TOKEN=$(curl -s -X POST \
  http://localhost:8080/realms/healthcore/protocol/openid-connect/token \
  -d grant_type=password \
  -d client_id=agent-support \
  -d client_secret=agent-support-dev-secret \
  -d username=coordinator \
  -d password=coordinator \
  -d scope="openid incidents:read incidents:write inventory:read" \
  | jq -r .access_token)

echo "KC_TOKEN length=${#KC_TOKEN}"
```

**Pass:** length ~800–1000, not `0`. Prefix should look like `eyJ…`.

### 4b. FastAPI token (`$API_TOKEN`)

**What:** HealthCore login JWT for incident API calls via `X-Downstream-Authorization`.

Register once (email must be a normal domain — **not** `.local`):

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"mcp-smoke@example.com","password":"password123","name":"MCP Smoke"}' \
  | jq .
```

(If already registered, ignore “already registered” and login.)

```bash
API_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"mcp-smoke@example.com","password":"password123"}' \
  | jq -r .access_token)

echo "API_TOKEN length=${#API_TOKEN}"
curl -s http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $API_TOKEN" | jq .
```

**Pass:** `/auth/me` returns user JSON, not `401`.

### 4c. Readonly Keycloak token (`$KC_READONLY`) — for Step 5.7

**What:** Same client, user `readonly`, **without** requesting `incidents:write`.

```bash
KC_READONLY=$(curl -s -X POST \
  http://localhost:8080/realms/healthcore/protocol/openid-connect/token \
  -d grant_type=password \
  -d client_id=agent-support \
  -d client_secret=agent-support-dev-secret \
  -d username=readonly \
  -d password=readonly \
  -d scope="openid incidents:read inventory:read" \
  | jq -r .access_token)

echo "KC_READONLY length=${#KC_READONLY}"
```

---

## Step 5 — Validation checks (Terminal D)

Remint `$KC_TOKEN` / `$API_TOKEN` anytime auth fails mid-session.

### 5.1 PRM (public discovery)

**What:** Confirms the server advertises itself as an OAuth protected resource (RFC 9728).

```bash
curl -s http://localhost:9000/.well-known/oauth-protected-resource | jq .
```

**Pass:** `resource` = `http://localhost:9000/mcp`, scopes listed.

### 5.2 Unauthenticated → 401

**What:** Confirms bearer middleware rejects requests with no/invalid token and challenges with PRM URL.

> **Trailing slash:** Starlette may **307** redirect `/mcp` → `/mcp/`. Bare `curl` without `-L` stops at the redirect and you won’t see the 401. Use `/mcp/` (or `curl -siL …/mcp`).

```bash
curl -si http://localhost:9000/mcp/ | head -n 25
curl -si http://localhost:9000/mcp/ \
  -H "Authorization: Bearer not-a-real-token" | head -n 25
```

**Pass:** both **401**; `WWW-Authenticate` mentions `oauth-protected-resource`.

### 5.3 List tools (discovery)

**What:** Authenticated MCP client lists tools (proves JWT + Streamable HTTP + tool registration).

```bash
# remint if > ~5 min since last mint
KC_TOKEN=$(curl -s -X POST \
  http://localhost:8080/realms/healthcore/protocol/openid-connect/token \
  -d grant_type=password \
  -d client_id=agent-support \
  -d client_secret=agent-support-dev-secret \
  -d username=coordinator \
  -d password=coordinator \
  -d scope="openid incidents:read incidents:write inventory:read" \
  | jq -r .access_token)

npx @modelcontextprotocol/inspector --cli \
  http://localhost:9000/mcp \
  --transport http \
  --method tools/list \
  --header "Authorization: Bearer $KC_TOKEN"
```

**Pass:** tools include `manage_incident_ticket` and `query_inventory`.

If you see `auth_required` / DCR / `Trusted Hosts`: MCP returned 401 and Inspector tried OAuth — remint `$KC_TOKEN` and retry CLI; do not use OAuth UI.

### 5.4 Inventory read

**What:** MCP tool calls live `GET /api/v1/inventory/products` and filters by `name_hint`.

```bash
npx @modelcontextprotocol/inspector --cli \
  http://localhost:9000/mcp \
  --transport http \
  --method tools/call \
  --tool-name query_inventory \
  --tool-arg name_hint=mask \
  --header "Authorization: Bearer $KC_TOKEN"
```

**Pass:** `"ok": true`, non-empty `products` / `matched`.  
**Fail `UPSTREAM_ERROR`:** API `:8000` is down — restart Step 2.

### 5.5 Incident round-trip

**What:** Create → update_status → get against live incidents API using **both** tokens.

**Status chain:** create always starts as `open`. Allowed updates: `open` → `in_progress` → `resolved` / `discarded`.

**API user for incidents:** `mcp-smoke@example.com` / `password123` (via `$API_TOKEN`).

```bash
# ensure API_TOKEN still valid
API_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"mcp-smoke@example.com","password":"password123"}' \
  | jq -r .access_token)

npx @modelcontextprotocol/inspector --cli \
  http://localhost:9000/mcp \
  --transport http \
  --method tools/call \
  --tool-name manage_incident_ticket \
  --tool-arg action=create \
  --tool-arg title="MCP smoke test" \
  --tool-arg description="Created from Inspector CLI" \
  --tool-arg category=ADMINISTRATIVE \
  --tool-arg origin=internal \
  --tool-arg branch=US-TX-01 \
  --header "Authorization: Bearer $KC_TOKEN" \
  --header "X-Downstream-Authorization: Bearer $API_TOKEN"
```

**Pass (create):** `"ok": true`, `incident.id`, and **`"status": "open"`**. Copy that id:

```bash
INCIDENT_ID=<id from create>   # e.g. INCIDENT_ID=99
```

#### Update status (must change `status`)

Run as **one unbroken command** (do not split `inspector` across lines). Expect the tool response itself to show the **new** status — that is the proof the update worked.

```bash
npx @modelcontextprotocol/inspector --cli \
  http://localhost:9000/mcp \
  --transport http \
  --method tools/call \
  --tool-name manage_incident_ticket \
  --tool-arg action=update_status \
  --tool-arg ticket_id=$INCIDENT_ID \
  --tool-arg status=in_progress \
  --header "Authorization: Bearer $KC_TOKEN" \
  --header "X-Downstream-Authorization: Bearer $API_TOKEN"
```

**Pass (update):** `"ok": true` and **`"status": "in_progress"`** (changed from create’s `open`). `updated_at` should be newer than `created_at`.

Optional second transition (same pattern):

```bash
npx @modelcontextprotocol/inspector --cli \
  http://localhost:9000/mcp \
  --transport http \
  --method tools/call \
  --tool-name manage_incident_ticket \
  --tool-arg action=update_status \
  --tool-arg ticket_id=$INCIDENT_ID \
  --tool-arg status=resolved \
  --header "Authorization: Bearer $KC_TOKEN" \
  --header "X-Downstream-Authorization: Bearer $API_TOKEN"
```

**Pass:** `"status": "resolved"`.

#### Get (verify)

`get` always needs **`ticket_id`** plus **both** headers (same as create/update).

```bash
npx @modelcontextprotocol/inspector --cli \
  http://localhost:9000/mcp \
  --transport http \
  --method tools/call \
  --tool-name manage_incident_ticket \
  --tool-arg action=get \
  --tool-arg ticket_id=$INCIDENT_ID \
  --header "Authorization: Bearer $KC_TOKEN" \
  --header "X-Downstream-Authorization: Bearer $API_TOKEN"
```

**Pass (get):** `"ok": true`; `status` matches the last update (`in_progress` or `resolved`).

| Error | Cause |
|-------|--------|
| HTTP **401** upstream | Bad/missing `$API_TOKEN` |
| HTTP **400** upstream | Invalid category/origin/branch, or illegal status transition |
| `AUTH_MISSING_TOKEN` | Forgot `X-Downstream-Authorization` |
| Status unchanged after update | Wrong `$INCIDENT_ID`, expired tokens, or command line broke (`inspec` / `tor`) |

Negative check (omit downstream header):

```bash
npx @modelcontextprotocol/inspector --cli \
  http://localhost:9000/mcp \
  --transport http \
  --method tools/call \
  --tool-name manage_incident_ticket \
  --tool-arg action=get \
  --tool-arg ticket_id=$INCIDENT_ID \
  --header "Authorization: Bearer $KC_TOKEN"
```

**Pass:** `"ok": false`, `AUTH_MISSING_TOKEN`.

### 5.6 Inventory write rejection

**What:** Proves write-shaped inventory input is rejected before any HTTP call.

```bash
cd /workspaces/chitrasharath_healthcore_ft_ai_1
uv run pytest mcps/company-tools/tests/test_tools.py::test_inventory_write_shaped_rejected -q
```

**Pass:** pytest green (`INVENTORY_WRITE_FORBIDDEN`).

### 5.7 Insufficient scope

**What:** Readonly Keycloak token lacks `incidents:write`; MCP must deny create.

**Must** send `Authorization: Bearer $KC_READONLY` (not `$KC_TOKEN`).

```bash
KC_READONLY=$(curl -s -X POST \
  http://localhost:8080/realms/healthcore/protocol/openid-connect/token \
  -d grant_type=password \
  -d client_id=agent-support \
  -d client_secret=agent-support-dev-secret \
  -d username=readonly \
  -d password=readonly \
  -d scope="openid incidents:read inventory:read" \
  | jq -r .access_token)

npx @modelcontextprotocol/inspector --cli \
  http://localhost:9000/mcp \
  --transport http \
  --method tools/call \
  --tool-name manage_incident_ticket \
  --tool-arg action=create \
  --tool-arg title="Should fail" \
  --tool-arg description="readonly user cannot write" \
  --tool-arg category=ADMINISTRATIVE \
  --tool-arg origin=internal \
  --tool-arg branch=US-TX-01 \
  --header "Authorization: Bearer $KC_READONLY" \
  --header "X-Downstream-Authorization: Bearer $API_TOKEN"
```

**Pass:** `"ok": false`, `error_code`: `AUTH_INSUFFICIENT_SCOPE`.  
**Fail if create succeeds:** wrong Authorization header, or realm still defaulting write — recreate Keycloak (see Troubleshooting).

### 5.8 RAG routing unchanged (optional)

**What:** Agent should answer policy questions via RAG only (no MCP tools). Needs `LLM_API_KEY`.

```bash
curl -s http://localhost:8000/api/v1/agent/query \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Do you take Medicaid in the US?"}' \
  | jq '{answer, sources_used}'
```

**Pass:** policy answer; `sources_used: ["rag"]`.

---

## Checklist

| # | Check | Pass when |
|---|--------|-----------|
| 1 | Keycloak | OIDC discovery `200` |
| 2 | API | `/docs` `200` |
| 3 | MCP | PRM JSON |
| 4 | Tokens | `$KC_TOKEN` / `$API_TOKEN` work |
| 5.1 | PRM | resource + scopes |
| 5.2 | Auth reject | 401 + `WWW-Authenticate` |
| 5.3 | Discovery | both tools listed |
| 5.4 | Inventory | `ok: true` + matched |
| 5.5 | Incidents | create → update → get |
| 5.6 | Write forbid | pytest pass |
| 5.7 | Scope deny | `AUTH_INSUFFICIENT_SCOPE` |
| 5.8 | RAG | `sources_used: ["rag"]` |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|--------|-----|
| MCP exit **69** | Keycloak not ready | Wait for OIDC `200`, restart MCP |
| MCP exit **78** | Missing env | Fix root `.env` or export vars |
| Port 9000 in use | MCP already running | Keep using it; don’t start a second |
| `auth_required` / DCR / Trusted Hosts | Inspector tried OAuth after MCP 401 | Remint `$KC_TOKEN`; use CLI `--header` only |
| Inventory `UPSTREAM_ERROR` | API down | Restart uvicorn on `:8000` |
| Incident HTTP **401** | Bad/empty `$API_TOKEN` | Remint login; check `API_TOKEN length` |
| Incident HTTP **400** | Bad enums | Use `ADMINISTRATIVE` / `internal` / `US-TX-01` |
| 5.7 create succeeds | Missing `$KC_READONLY` header or write still default scope | Fix header; recreate Keycloak |
| Curl `/mcp` shows **307** only | Redirect to `/mcp/` | Use `http://localhost:9000/mcp/` or `curl -siL` |

**Recreate Keycloak** (realm import only on first container create):

```bash
docker compose stop keycloak && docker compose rm -f keycloak
docker compose up -d keycloak
# wait for OIDC 200, remint tokens, restart MCP if it exited 69
```

### Codespaces

Forward **8080**, **8000**, **9000**. Keep Keycloak `iss` aligned with `OIDC_ISSUER`.

---

## Exit codes (MCP)

| Code | Meaning |
|------|---------|
| 0 | Clean shutdown |
| 1 | Fatal error |
| 78 | Config error |
| 69 | Cannot reach OIDC issuer / JWKS |

## Automated tests (offline)

```bash
cd /workspaces/chitrasharath_healthcore_ft_ai_1
uv run pytest mcps/company-tools/tests -q
uv run pytest tests/pipelines/test_agent_evals.py services/api/tests/test_agent.py -q
```
