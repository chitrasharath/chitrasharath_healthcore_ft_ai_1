# HealthCore API (`services/api`)

FastAPI modular monolith for HealthCore internal tools. Domains include incidents reporting, supplier directory, medical supply inventory, and JWT authentication with password reset.

## Architecture

The API uses **two databases**:

| Database | Purpose | Access |
|----------|---------|--------|
| **TinyDB** (`db.json`) | Users, auth tokens, suppliers | `get_db()` |
| **Supabase (PostgreSQL)** | Medical supplies, incidents (CRUD), deliveries, consumptions | `get_supabase_db()` |

Inventory stock is **computed**, never stored: `SUM(deliveries) − SUM(consumptions)`.

## Setup

```bash
cd services/api
uv sync --extra dev
cp .example.env .env
```

Required in `.env`:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing secret (override in non-local environments) |
| `JWT_EXPIRE_MINUTES` | Access token lifetime |

Optional:

| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:3001` | Comma-separated allowed origins |
| `EMAIL_API_KEY` | (empty) | Resend API key; when empty, reset links print to stdout |
| `FRONTEND_URL` | `http://localhost:3001` | Base URL for password-reset email links |
| `DATABASE_URL` | (empty) | Supabase PostgreSQL URI; required for inventory, incident manager, and related seed |

### Supabase (`DATABASE_URL`)

Inventory and incident-manager data live in Supabase project **`milestone5_inventory`**. Copy the **Transaction pooler** URI from Supabase Dashboard → Project Settings → Database.

```env
DATABASE_URL=postgresql://postgres.[ref]:[url-encoded-password]@aws-1-us-west-2.pooler.supabase.com:6543/postgres
```

Notes:

- Copy the exact host from the dashboard (pooler region varies, e.g. `aws-1-us-west-2` for this project).
- URL-encode special characters in the password (`$` → `%24`, etc.).
- Do not wrap the password in `[` `]` — those are placeholder markers in Supabase docs.
- Tables are created on API startup via `SQLModel.metadata.create_all()`.
- **Pytest does not need Supabase** — inventory tests use an in-memory SQLite override.

## Run

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive docs: http://localhost:8000/docs

## Seed

```bash
uv run seed
```

Idempotent seeder:

- **Suppliers** — 15 records in TinyDB (skips existing names).
- **Inventory** — 6 supplies, 4 deliveries, 3 consumptions in Supabase (skips if supplies already exist; order records only on first insert).

Requires `DATABASE_URL` for the inventory portion. Supplier seed runs regardless.

## Test

```bash
uv run pytest
```

Tests force `EMAIL_API_KEY=""` and `DATABASE_URL=""` so runs are deterministic and do not hit live Supabase.

## Authentication

Passwords are bcrypt-hashed. Protected routes require `Authorization: Bearer <token>`.

Plans: [`IMPLEMENTATION_PLAN_auth_1.md`](../../memory-bank/references/authentication_backend_ai_plan/IMPLEMENTATION_PLAN_auth_1.md), [`IMPLEMENTATION_PLAN_auth_2_3.md`](../../memory-bank/references/authentication_backend_ai_plan/IMPLEMENTATION_PLAN_auth_2_3.md)

### Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/auth/register` | POST | No | Register; returns JWT (`201`) |
| `/api/v1/auth/login` | POST | No | Login; returns JWT (`200`) |
| `/api/v1/auth/me` | GET | Yes | Current user profile |
| `/api/v1/auth/forgot-password` | POST | No | Request reset link (generic response) |
| `/api/v1/auth/reset-password` | POST | No | Set new password with reset token |
| `/api/v1/users` | POST | No | Create user (no token returned) |
| `/api/v1/users` | GET | Yes | List all users |
| `/api/v1/users/{id}` | GET | Yes | Get user by id |
| `/api/v1/users/{id}` | PUT | Yes | Update own record only (`403` otherwise) |
| `/api/v1/users/{id}` | DELETE | Yes | Delete user (`204`) |
| `/api/v1/incidents/analyze` | POST | Yes | Upload incident CSV for aggregate analysis |
| `/api/v1/incidents/results/export` | GET | Yes | Export last CSV analysis results |
| `/api/v1/incidents` | POST | Yes | Create incident (incident manager) |
| `/api/v1/incidents` | GET | Yes | List incidents (`?status`, `?origin`, `?branch`, `?category`) |
| `/api/v1/incidents/summary` | GET | Yes | Summary dashboard counts |
| `/api/v1/incidents/{id}` | GET | Yes | Incident detail |
| `/api/v1/incidents/{id}` | PATCH | Yes | Update incident fields |
| `/api/v1/incidents/{id}/status` | PATCH | Yes | Update incident status |
| `/api/v1/suppliers` | GET, POST | Yes | List or register suppliers |
| `/api/v1/suppliers/{id}` | GET, DELETE | Yes | Supplier detail; DELETE soft-suspends |
| `/api/v1/suppliers/{id}/rate` | PATCH | Yes | Update monthly rate |
| `/api/v1/suppliers/{id}/status` | PATCH | Yes | Activate or suspend supplier |
| `/api/v1/suppliers/{id}/details` | PATCH | Yes | Update optional fields |
| `/api/v1/inventory/products` | GET | No | List supplies with computed `current_stock` |
| `/api/v1/inventory/products` | POST | Yes | Register a new supply (`current_stock: 0`) |
| `/api/v1/inventory/products/{id}` | GET | No | Single supply with computed stock |
| `/api/v1/inventory/orders/inbound` | POST | Yes | Log vendor delivery (increases stock) |
| `/api/v1/inventory/orders/outbound` | POST | Yes | Log consumption (decreases stock; `400` if insufficient) |
| `/api/v1/inventory/orders` | GET | No | Combined delivery + consumption history |

Inventory plans: [`milestone5_backend_implementation_plan.md`](../../memory-bank/references/milestone5_ai_plan/milestone5_backend_implementation_plan.md), [`milestone5_frontend_implementation_plan.md`](../../memory-bank/references/milestone5_ai_plan/milestone5_frontend_implementation_plan.md)

Backoffice UI: `/inventory` on landing (`uis/backoffice/landing/`, port **3001**). Module source: `uis/backoffice/inventory/`.

### Example flow

```bash
# Register
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"password123"}'

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"password123"}' | jq -r .access_token)

# Protected route
curl -s http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"

# Inventory — create product (auth required)
curl -s -X POST http://localhost:8000/api/v1/inventory/products \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Nitrile gloves","sku":"HCR-TEST-001","category":"ppe","unit":"box","country":"US"}'

# Inventory — list products (public)
curl -s http://localhost:8000/api/v1/inventory/products
```

Use `/docs` → **Authorize** to paste the token for interactive testing.
