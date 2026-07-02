---
name: Milestone 5 Inventory Backend
overview: "Build a medical supply inventory API at services/api: SQLModel + Supabase for supplies/deliveries/consumptions alongside existing TinyDB auth, 6 REST endpoints under /api/v1/inventory/, idempotent seed, and SQLite-backed pytest. Backend-only; no UI in this milestone."
todos:
  - id: step0-branch-deps
    content: Create feature/milestone5 branch; add sqlmodel + psycopg2-binary to pyproject.toml; uv sync
    status: pending
  - id: step1-supabase-project
    content: Create Supabase project milestone5_inventory (if none exists); obtain DATABASE_URL pooler URI; update .example.env
    status: pending
  - id: step2-core-infra
    content: Add database_url to config.py; get_supabase_db + conditional engine in db.py; startup create_all in main.py
    status: pending
  - id: step3-router-register
    content: Register inventory router in app/api/v1/router.py without router-level auth
    status: pending
  - id: step4-models-schemas
    content: Create inventory/models.py (3 SQLModel tables) and inventory/schemas.py (Pydantic DTOs + validators)
    status: pending
  - id: step5-router-endpoints
    content: Implement inventory/router.py with compute_stock helper and all 6 endpoints
    status: pending
  - id: step6-seed
    content: Create inventory/seed.py (idempotent); wire seed_inventory() into app/seed.py main()
    status: pending
  - id: step7-tests
    content: Update tests/conftest.py DATABASE_URL guard; add tests/test_inventory.py with 10 spec cases
    status: pending
  - id: step8-verify
    content: Run uv run pytest, uv run seed, manual Swagger smoke; confirm acceptance checklist §14
    status: pending
  - id: step9-docs
    content: Update memory-bank/progress.md and decisions.md after verify passes
    status: pending
isProject: false
---

# Milestone 5 — Inventory Backend Implementation Plan

**Plan file:** [`memory-bank/references/milestone5_ai_plan/milestone5_backend_implementation_plan.md`](milestone5_backend_implementation_plan.md)

**Requirements source:** [`milestone5_backend_specs.md`](milestone5_backend_specs.md)

**Milestone:** 5 — Medical Supply Inventory Management (Backend)

**Branch:** `feature/milestone5` (off `main`)

**Working directory:** `services/api/`

**Status:** Delivered — backend, tests, and seed complete (82 pytest passing)

---

## Executive summary

HealthCore operates 12 outpatient clinics with no central visibility into medical supply stock. Each location tracked inventory in local spreadsheets. This milestone adds a **centralised inventory REST API** to the existing FastAPI backend so clinic operations can register supplies, log vendor deliveries (stock in), log clinical consumptions (stock out), and query computed stock levels and order history.

The implementation introduces HealthCore's **first Supabase (PostgreSQL) integration** while keeping TinyDB for users and authentication unchanged. Stock is **never stored directly** — it is always computed as `SUM(deliveries) − SUM(consumptions)`.

**Scope:** Backend API only (`services/api/`). No Next.js dashboard in this milestone.

---

## Planning decisions (locked)

These resolve ambiguities between the spec, stakeholder context, and the current codebase.

| Topic | Decision |
|-------|----------|
| Auth on GET endpoints | **Public reads** — `GET /products`, `GET /products/{id}`, `GET /orders` require no token; POST endpoints require JWT (per spec §10.3 table) |
| Supabase project name | **`milestone5_inventory`** — use this exact name when creating the project (dashboard or MCP) |
| Supabase setup | **Create project first**, then copy pooler connection string (port 6543) into `.env`; MCP can create/verify project; schema via `create_all` on startup — no SQL migrations; **pytest does not need Supabase** (SQLite override) |
| Domain layout | **Flat spec layout** — `models.py`, `schemas.py`, `router.py`, `seed.py` only; business logic in router (not `service.py` / `store.py` like suppliers) |
| Router registration | Include inventory router in `app/api/v1/router.py` **without** router-level `Depends(get_current_user)` |
| Dependency install | Use **`uv sync --all-extras`** (project standard), not raw `pip install` |
| Test database | **In-memory SQLite** via FastAPI `dependency_overrides` on `get_supabase_db`; force `DATABASE_URL=""` in `conftest.py` |
| Seed trigger | **Manual** — `uv run seed` after startup; inventory seed runs after supplier seed in same command |
| Seed order records | Insert deliveries/consumptions **only on first supply insert** (idempotent re-runs skip duplicate orders) |
| Seed `user_uuid` | Use `"1"` string per spec — no FK to TinyDB; valid even without a user with id 1 |
| Protected code | Do **not** modify `auth/`, `users/`, `procurement/`, `reporting/`, or `dependencies.py` |
| ORM choice | **SQLModel only** — no raw SQLAlchemy models |
| Memory-bank updates | Update `progress.md` and `decisions.md` **only after** full pytest + smoke verify pass |

---

## Current codebase baseline

Exploration against `services/api/` (as of plan authoring):

| Area | Current state |
|------|---------------|
| Inventory domain | **Does not exist** — no `app/domains/inventory/` |
| Persistence | TinyDB only via `get_db()` in `app/core/db.py` |
| ORM | None — Pydantic schemas + dict documents |
| Config | No `database_url` field in `app/core/config.py` |
| Startup | No table creation in `app/main.py` |
| Dependencies | No `sqlmodel` or `psycopg2-binary` in `pyproject.toml` |
| Tests | 70 passing — 37 auth, 29 suppliers, 4 incidents |
| Seed | Suppliers only (`uv run seed` → 15 records) |

**Reference domain pattern (suppliers):** `router → service → store` with TinyDB. Inventory **intentionally diverges** — spec mandates logic in `router.py` with SQLModel models.

**Existing auth integration point:** `get_current_user` in `app/core/dependencies.py` returns a user dict with integer `"id"` from TinyDB. Store `str(current_user["id"])` as `user_uuid` on orders.

---

## Architecture

### Dual-database model

| Database | Purpose | Dependency |
|----------|---------|------------|
| **TinyDB** (`db.json`) | Users, JWT auth, suppliers, reset tokens | `get_db()` — unchanged |
| **Supabase (PostgreSQL)** | Medical supplies, deliveries, consumptions | `get_supabase_db()` — new |

No user data is replicated in Supabase. Order records store `user_uuid` as a plain string referencing the TinyDB user who created them.

### Request flow

```mermaid
flowchart TB
    subgraph clients [Clients]
        Swagger[Swagger / TestClient]
        FutureUI[Future ops dashboard]
    end

    subgraph api [services/api]
        V1["api/v1/router.py"]
        Inv["inventory/router.py"]
        AuthDep["get_current_user"]
        SupaDep["get_supabase_db"]
        TinyDep["get_db"]
    end

    subgraph data [Persistence]
        TinyDB["db.json"]
        PG["Supabase PostgreSQL"]
    end

    Swagger --> V1
    FutureUI --> V1
    V1 --> Inv
    Inv -->|"POST only"| AuthDep
    Inv --> SupaDep
    AuthDep --> TinyDep
    TinyDep --> TinyDB
    SupaDep --> PG
```

### Stock computation rule

```
current_stock(supply_id) = SUM(SupplyDelivery.quantity WHERE supply_id)
                         − SUM(SupplyConsumption.quantity WHERE supply_id)
```

- No `current_stock` column in the database.
- Included in `MedicalSupplyRead` response schema only.
- New products always start at `current_stock = 0`.

---

## Business rules (non-negotiable)

From spec §3 and §13 — the evaluator will test these:

1. **Stock is computed, never stored** — no direct stock column or mutation endpoint.
2. **No direct stock mutation** — only `SupplyDelivery` (inbound) and `SupplyConsumption` (outbound) change inventory.
3. **Negative stock prevention** — outbound orders that would exceed available stock return HTTP 400:
   ```
   Insufficient stock for supply '{name}'. Available: {available}, requested: {quantity}.
   ```
4. **Order traceability** — every delivery/consumption records `user_uuid` of the authenticated creator.
5. **Consumption type validation** — only `"clinical_use"` or `"expiry_waste"`; other values → 422.
6. **US and UK supplies coexist** — `country` field (`"US"` or `"UK"`) on `MedicalSupply`.
7. **Clinic IDs are plain integers** — range 1–12; not foreign keys in this milestone.
8. **Separate ORM and Pydantic files** — `models.py` vs `schemas.py`.
9. **Never return raw ORM objects** — always map to Pydantic response schemas.
10. **No N+1 on GET /orders** — batch-fetch supplies, do not query per order in a loop.

---

## API surface

All routes mounted under `/api/v1/inventory/` (inventory router prefix `/inventory` + v1 prefix `/api/v1`).

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/inventory/products` | No | List all supplies with computed `current_stock` |
| `POST` | `/inventory/products` | Yes | Register a new supply; returns `current_stock: 0` |
| `GET` | `/inventory/products/{id}` | No | Single supply with stock; 404 if missing |
| `POST` | `/inventory/orders/inbound` | Yes | Log vendor delivery; increases stock |
| `POST` | `/inventory/orders/outbound` | Yes | Log consumption; decreases stock; 400 if insufficient |
| `GET` | `/inventory/orders` | No | Combined delivery + consumption history |

### Error responses

| Condition | Status | Detail |
|-----------|--------|--------|
| Product not found | 404 | `"Product not found"` |
| Insufficient stock | 400 | `"Insufficient stock for supply '{name}'. Available: {available}, requested: {quantity}."` |
| Invalid consumption_type | 422 | Pydantic validation error |
| Missing/invalid JWT on POST | 401 | Standard OAuth2 bearer failure |

---

## Implementation steps

### Step 0 — Branch and dependencies

```bash
git checkout main && git pull
git checkout -b feature/milestone5
```

Add to [`services/api/pyproject.toml`](../../../services/api/pyproject.toml) `[project] dependencies`:

```toml
"sqlmodel>=0.0.22",
"psycopg2-binary>=2.9.0",
```

Install:

```bash
cd services/api
uv sync --all-extras
```

**Verify:** `uv run python -c "import sqlmodel; import psycopg2"` succeeds.

---

### Step 1 — Supabase project creation and environment setup

Supabase must exist **before** you can copy a connection string. Implementation and pytest can proceed without this step (tests use in-memory SQLite), but you need a live project for `uv run seed` against PostgreSQL and manual Swagger smoke tests (Step 8).

#### 1.1 Check for an existing project

**Via Supabase MCP (during implementation):**

1. `list_projects` — if **`milestone5_inventory`** already exists, skip to §1.3.
2. If none exists, `list_organizations` → pick the target org.

**Via Supabase Dashboard:**

1. Sign in at [supabase.com/dashboard](https://supabase.com/dashboard).
2. Check whether an existing project should be reused or a new one is needed.

#### 1.2 Create a new project (if none exists)

**Option A — Supabase Dashboard (simplest for first-time setup):**

1. Click **New project**.
2. Choose **organization** and set:
   - **Name:** `milestone5_inventory` (required — use this exact name)
   - **Database password:** generate and **save securely** — required for the connection string
   - **Region:** e.g. `us-east-1` (US clinics) or `eu-west-2` (UK proximity)
3. Wait 2–5 minutes until the project status is **Active** (green).

**Option B — Supabase MCP (agent-assisted during implementation):**

1. `list_organizations` → note `organization_id`.
2. `get_cost` + `confirm_cost` for the chosen org/region (required before creation).
3. `create_project` with `name: "milestone5_inventory"`, `region`, `organization_id`, `confirm_cost_id`.
4. Poll `get_project` until status is active (provisioning takes a few minutes).
5. **Save the database password** from the creation flow — the MCP does not expose a Postgres URI directly; you still retrieve the connection string from the dashboard (§1.3).

**Do not commit** the database password or full connection string to git.

#### 1.3 Get the `DATABASE_URL` connection string

After the project is active:

1. Supabase Dashboard → **Project Settings → Database → Connection string**
2. Select **URI** tab and **Transaction pooler** mode (port `6543`)
3. Copy the URI and replace `[YOUR-PASSWORD]` with the password from §1.2
4. Add to `services/api/.env`:

```env
DATABASE_URL=postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
```

**Verify connectivity (optional, after Step 2 core infra is in place):**

```bash
cd services/api
uv run python -c "from sqlmodel import create_engine; create_engine('$DATABASE_URL').connect(); print('ok')"
```

#### 1.4 Update `.example.env`

Add a commented placeholder to [`services/api/.example.env`](../../../services/api/.example.env) (no real credentials):

```env
# PostgreSQL connection for inventory — create Supabase project first, then copy pooler URI
# DATABASE_URL=postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
```

#### 1.5 Alternatives and fallbacks

| Option | When to use |
|--------|-------------|
| Direct connection (port 5432) | Pooler unavailable; less ideal for dev reload |
| Supabase MCP `list_tables` / `get_logs` | Verify tables after first API startup; debug seed issues |
| Skip Supabase until Step 8 | **Valid** — implement Steps 0–7 and run `uv run pytest` with SQLite only |
| SQLite locally for manual dev | Quick experiments only; milestone target is Supabase for real runs |

**Note:** `.env` is gitignored. Never commit credentials.

**Sequencing summary:**

```
Create Supabase project `milestone5_inventory` → copy pooler DATABASE_URL → .env
         ↓
Implement code (Steps 2–7) — pytest works without Supabase
         ↓
Start API (create_all creates tables) → uv run seed → manual smoke (Step 8)
```

---

### Step 2 — Core infrastructure

#### 2.1 `app/core/config.py`

Add one field to `Settings`:

```python
database_url: str = ""
```

Empty default ensures existing tests boot without Supabase.

#### 2.2 `app/core/db.py`

Append **below** existing TinyDB code — do not modify `get_db()` or `reset_db()`:

```python
from sqlmodel import Session, create_engine

from app.core.config import settings

supabase_engine = None
if settings.database_url:
    supabase_engine = create_engine(settings.database_url, echo=False)


def get_supabase_db():
    with Session(supabase_engine) as session:
        yield session
```

**Rules:**
- Engine created only when `database_url` is non-empty.
- `get_supabase_db` is a generator yielding one `Session` per request.
- No global `Session` variable.

#### 2.3 `app/main.py`

Import models so they register with metadata before `create_all`:

```python
from sqlmodel import SQLModel

from app.core.db import supabase_engine
from app.domains.inventory import models as inventory_models  # noqa: F401


@app.on_event("startup")
def on_startup() -> None:
    if supabase_engine:
        SQLModel.metadata.create_all(supabase_engine)
```

#### 2.4 `app/api/v1/router.py`

```python
from app.domains.inventory.router import router as inventory_router

api_v1_router.include_router(inventory_router)
```

No `dependencies=[Depends(get_current_user)]` at include level — auth is per-endpoint inside inventory router.

---

### Step 3 — Inventory domain: models

Create `app/domains/inventory/models.py`:

#### `MedicalSupply` (`medical_supply`)

| Column | Type | Notes |
|--------|------|-------|
| `id` | int, PK | Auto-increment |
| `name` | str | Required |
| `sku` | str | Required |
| `category` | str | `ppe`, `wound_care`, `diagnostics`, `medications`, `consumables` |
| `unit` | str | `box`, `unit`, `pack`, `vial` |
| `country` | str | `"US"` or `"UK"` |

**No `current_stock` column.**

#### `SupplyDelivery` (`supply_delivery`)

| Column | Type | Notes |
|--------|------|-------|
| `id` | int, PK | Auto-increment |
| `supply_id` | int, FK | → `medical_supply.id` |
| `quantity` | int | Required |
| `vendor_name` | str | Required |
| `clinic_id` | int | 1–12 |
| `created_at` | datetime | UTC default `datetime.now(timezone.utc)` |
| `user_uuid` | str | `str(current_user["id"])` |

#### `SupplyConsumption` (`supply_consumption`)

| Column | Type | Notes |
|--------|------|-------|
| `id` | int, PK | Auto-increment |
| `supply_id` | int, FK | → `medical_supply.id` |
| `quantity` | int | Required |
| `consumption_type` | str | `"clinical_use"` or `"expiry_waste"` |
| `clinic_id` | int | 1–12 |
| `created_at` | datetime | UTC default |
| `user_uuid` | str | Authenticated user id as string |

Foreign keys: `Field(foreign_key="medical_supply.id")` — table name, not class name.

---

### Step 4 — Inventory domain: schemas

Create `app/domains/inventory/schemas.py` — pure Pydantic `BaseModel` (NOT SQLModel):

| Schema | Purpose |
|--------|---------|
| `MedicalSupplyCreate` | POST body: name, sku, category, unit, country |
| `MedicalSupplyRead` | Response: all supply fields + computed `current_stock: int` |
| `SupplyDeliveryCreate` | POST body: supply_id, quantity, vendor_name, clinic_id |
| `SupplyDeliveryRead` | Response: all delivery fields including user_uuid, created_at |
| `SupplyConsumptionCreate` | POST body + `@field_validator` on consumption_type |
| `SupplyConsumptionRead` | Response: all consumption fields |
| `OrderRead` | Combined order history for GET /orders |

`OrderRead` fields:

```python
id: int
order_type: str          # "inbound" or "outbound"
supply_id: int
supply_name: str
quantity: int
user_uuid: str
created_at: datetime
vendor_name: str | None = None       # inbound only
consumption_type: str | None = None  # outbound only
clinic_id: int
```

Consumption type validator:

```python
@field_validator("consumption_type")
@classmethod
def validate_consumption_type(cls, v: str) -> str:
    allowed = ("clinical_use", "expiry_waste")
    if v not in allowed:
        raise ValueError(f"consumption_type must be one of {allowed}")
    return v
```

All read schemas: `model_config = {"from_attributes": True}`.

---

### Step 5 — Inventory domain: router

Create `app/domains/inventory/router.py`:

```python
router = APIRouter(prefix="/inventory")
```

#### `compute_stock` helper

```python
def compute_stock(session: Session, supply_id: int) -> int:
    inbound = session.exec(
        select(func.coalesce(func.sum(SupplyDelivery.quantity), 0))
        .where(SupplyDelivery.supply_id == supply_id)
    ).one()
    outbound = session.exec(
        select(func.coalesce(func.sum(SupplyConsumption.quantity), 0))
        .where(SupplyConsumption.supply_id == supply_id)
    ).one()
    return inbound - outbound
```

#### Endpoint implementation notes

**GET /products**
- `select(MedicalSupply)` → for each row, call `compute_stock` → build `MedicalSupplyRead`.

**POST /products**
- `Depends(get_current_user)` required.
- Insert `MedicalSupply`, commit, refresh.
- Return `MedicalSupplyRead` with `current_stock=0`.

**GET /products/{id}**
- Fetch by id; 404 `"Product not found"` if missing.
- Return with computed stock.

**POST /orders/inbound**
- Auth required.
- Validate supply exists (404 if not).
- Set `user_uuid=str(current_user["id"])`.
- Return `SupplyDeliveryRead`.

**POST /orders/outbound**
- Auth required.
- Validate supply exists (404).
- `available = compute_stock(session, supply_id)`.
- If `body.quantity > available`: HTTP 400 with exact message including supply name.
- Set `user_uuid=str(current_user["id"])`.
- Return `SupplyConsumptionRead`.

**GET /orders**
- Query all `SupplyDelivery` and `SupplyConsumption` rows.
- Collect unique `supply_id`s → single batch query for `MedicalSupply` → build `{id: supply}` dict.
- Map each delivery to `OrderRead(order_type="inbound", vendor_name=..., consumption_type=None)`.
- Map each consumption to `OrderRead(order_type="outbound", consumption_type=..., vendor_name=None)`.
- Merge lists; sort by `created_at` descending (implementation default — spec does not mandate order).

#### Response mapping pattern

```python
def to_supply_read(supply: MedicalSupply, stock: int) -> MedicalSupplyRead:
    return MedicalSupplyRead(
        id=supply.id,
        name=supply.name,
        sku=supply.sku,
        category=supply.category,
        unit=supply.unit,
        country=supply.country,
        current_stock=stock,
    )
```

Never return raw SQLModel instances from route handlers.

---

### Step 6 — Seed data

Create `app/domains/inventory/seed.py` with `seed_inventory()`:

#### 6.1 Medical supplies (6 records)

| name | sku | category | unit | country |
|------|-----|----------|------|---------|
| Nitrile gloves (box of 100) | HCR-PPE-001 | ppe | box | US |
| Surgical mask (pack of 50) | HCR-PPE-002 | ppe | pack | UK |
| Adhesive wound dressing | HCR-WND-001 | wound_care | box | US |
| Rapid strep test kit | HCR-DIAG-001 | diagnostics | unit | US |
| Blood glucose test strips (50) | HCR-DIAG-002 | diagnostics | box | UK |
| 0.9% Saline solution 500ml | HCR-MED-001 | medications | vial | US |

#### 6.2 Deliveries (4 records — only on first seed)

| sku | quantity | vendor_name | clinic_id | user_uuid |
|-----|----------|-------------|-----------|-----------|
| HCR-PPE-001 | 100 | MedLine Industries | 1 | "1" |
| HCR-PPE-001 | 50 | Bound Tree Medical | 3 | "1" |
| HCR-PPE-002 | 200 | Cardinal Health UK | 10 | "1" |
| HCR-DIAG-001 | 30 | MedLine Industries | 5 | "1" |

#### 6.3 Consumptions (3 records — only on first seed)

| sku | quantity | consumption_type | clinic_id | user_uuid |
|-----|----------|------------------|-----------|-----------|
| HCR-PPE-001 | 20 | clinical_use | 1 | "1" |
| HCR-PPE-001 | 5 | expiry_waste | 3 | "1" |
| HCR-PPE-002 | 10 | clinical_use | 10 | "1" |

#### Idempotency rules

1. If `supabase_engine` is `None`, print skip message and return.
2. Check existing supplies by SKU — skip duplicates.
3. Track whether **any** supplies were newly inserted this run.
4. Insert deliveries and consumptions **only if** supplies were just created (first run).
5. Re-running seed must not duplicate order records.

Wire into [`app/seed.py`](../../../services/api/app/seed.py):

```python
from app.domains.inventory.seed import seed_inventory

def main() -> None:
    inserted, skipped = run_seed()
    print(f"Inserted {inserted} supplier(s). Skipped {skipped} existing.")
    seed_inventory()
```

---

### Step 7 — Tests

#### 7.1 `tests/conftest.py`

Add alongside existing env setup:

```python
os.environ.setdefault("DATABASE_URL", "")
os.environ["DATABASE_URL"] = ""  # force empty — prevents .env leaking into pytest
```

#### 7.2 `tests/test_inventory.py`

Fixtures **local to this file** (do not replace `client` fixtures in other test modules):

```python
from sqlmodel import SQLModel, Session, create_engine
from app.core.db import get_supabase_db
from app.main import app
from tests.auth_helpers import auth_headers

test_engine = create_engine("sqlite://")

@pytest.fixture(name="inventory_session")
def inventory_session_fixture():
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session
    SQLModel.metadata.drop_all(test_engine)

@pytest.fixture(name="client")
def client_fixture(inventory_session):
    def override():
        yield inventory_session
    app.dependency_overrides[get_supabase_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def bearer(client: TestClient) -> dict[str, str]:
    return auth_headers(client)
```

Import inventory models in test file (or via app import) so `create_all` registers all tables.

#### 7.3 Required test cases (spec §12.3)

| # | Test | Assertion |
|---|------|-----------|
| 1 | POST `/api/v1/inventory/products` | 201; `current_stock == 0`; requires Bearer |
| 2 | GET `/api/v1/inventory/products` | List includes correct computed stock after orders |
| 3 | GET `/api/v1/inventory/products/{id}` | 200 with stock; 404 for missing id |
| 4 | POST `/api/v1/inventory/orders/inbound` | Stock increases; requires auth |
| 5 | POST `/api/v1/inventory/orders/outbound` | Stock decreases; requires auth |
| 6 | Outbound over-consumption | 400 with exact message format from spec |
| 7 | Invalid `consumption_type: "stolen"` | 422 validation error |
| 8 | GET `/api/v1/inventory/orders` | Combined list with `order_type`, `supply_name` |
| 9 | POST without auth token | 401 |
| 10 | Multi-order stock net | After multiple inbound/outbound, `current_stock` is correct net |

**Regression target:** All existing 70 tests remain green.

---

### Step 8 — Verification

**Prerequisite:** Step 1 complete (Supabase project `milestone5_inventory` created, `DATABASE_URL` in `.env`) before `uv run seed` and live API smoke tests. `uv run pytest` runs without Supabase.

```bash
cd services/api
uv run pytest tests/ -v          # no Supabase required
uv run seed                      # requires DATABASE_URL in .env
uv run uvicorn app.main:app --reload --port 8000   # requires DATABASE_URL for inventory tables
```

Open `http://localhost:8000/docs` — inventory endpoints under `/api/v1/inventory/`.

**Manual smoke checklist:**

1. `POST /api/v1/auth/register` → copy Bearer token
2. `POST /api/v1/inventory/products` (auth) → new product with `current_stock: 0`
3. `GET /api/v1/inventory/products` → product appears with stock
4. `POST /api/v1/inventory/orders/inbound` → stock increases
5. `POST /api/v1/inventory/orders/outbound` (within stock) → stock decreases
6. `POST /api/v1/inventory/orders/outbound` (over limit) → 400
7. `GET /api/v1/inventory/orders` → merged inbound + outbound history

---

### Step 9 — Memory-bank updates

After verification passes, update:

- [`memory-bank/progress.md`](../../progress.md) — Milestone 5 inventory backend delivered
- [`memory-bank/decisions.md`](../../decisions.md) — dual-DB architecture, SQLModel/Supabase, public GET auth decision

---

## Acceptance criteria checklist

From spec §14 — all must pass before milestone is complete:

- [ ] `feature/milestone5` branch exists with all changes committed
- [ ] Supabase project named **`milestone5_inventory`** exists and is active
- [ ] `DATABASE_URL` in `.env` (not hardcoded); `.env` gitignored
- [ ] `pyproject.toml` includes `sqlmodel` and `psycopg2-binary`
- [ ] `app/core/db.py` has both TinyDB (`get_db`) and SQLModel (`get_supabase_db`)
- [ ] `app/core/config.py` has `database_url` field
- [ ] `app/main.py` calls `SQLModel.metadata.create_all()` on startup
- [ ] `models.py` defines `MedicalSupply`, `SupplyDelivery`, `SupplyConsumption`
- [ ] `MedicalSupply` has NO `current_stock` column
- [ ] Foreign keys: delivery/consumption `supply_id` → `medical_supply.id`
- [ ] `schemas.py` has separate Pydantic schemas with `MedicalSupplyRead.current_stock`
- [ ] `router.py` uses `APIRouter(prefix="/inventory")`
- [ ] All 6 endpoints functional under `/api/v1/inventory/...`
- [ ] GET products returns correctly computed `current_stock`
- [ ] Outbound with excessive quantity returns HTTP 400
- [ ] Invalid `consumption_type` returns validation error
- [ ] Auth-protected POST endpoints return 401 without token
- [ ] `user_uuid` on orders matches authenticated user's TinyDB id (as string)
- [ ] Seed data present (6 supplies, 4+ deliveries, 3+ consumptions)
- [ ] `tests/test_inventory.py` passes
- [ ] No N+1 queries in GET /orders
- [ ] Entity names match spec exactly

---

## File change summary

### Modify

| File | Change |
|------|--------|
| `services/api/pyproject.toml` | Add sqlmodel, psycopg2-binary |
| `services/api/.example.env` | Add commented DATABASE_URL |
| `services/api/app/core/config.py` | Add `database_url: str = ""` |
| `services/api/app/core/db.py` | Add supabase_engine + get_supabase_db |
| `services/api/app/main.py` | Model import + startup create_all |
| `services/api/app/api/v1/router.py` | Include inventory router |
| `services/api/app/seed.py` | Call seed_inventory() |
| `services/api/tests/conftest.py` | Force empty DATABASE_URL |

### Create

| File | Purpose |
|------|---------|
| `app/domains/inventory/__init__.py` | Package marker (empty) |
| `app/domains/inventory/models.py` | SQLModel ORM tables |
| `app/domains/inventory/schemas.py` | Pydantic request/response DTOs |
| `app/domains/inventory/router.py` | 6 endpoints + compute_stock |
| `app/domains/inventory/seed.py` | Idempotent inventory seed |
| `tests/test_inventory.py` | 10 inventory test cases |

### Do not modify

- `app/domains/auth/`
- `app/domains/users/`
- `app/domains/procurement/`
- `app/domains/reporting/`
- `app/core/dependencies.py`

---

## Risk register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Developer `.env` has `DATABASE_URL` during pytest | Tests hit live Supabase | Force `DATABASE_URL=""` in conftest (same pattern as `EMAIL_API_KEY`) |
| Models not imported before `create_all` | Empty/missing tables | Import `inventory.models` in `main.py` before startup |
| SQLite vs PostgreSQL dialect differences | Test/production drift | Use portable SQLModel queries; no PostgreSQL-specific SQL |
| `get_supabase_db` when engine is None | Runtime error on unconfigured env | Guard startup/seed with `if supabase_engine`; tests override dependency |
| Global `client` fixture name collision | Break other test modules | Keep inventory fixtures in `test_inventory.py` only |
| Spec seed `user_uuid="1"` without user seeder | Misleading audit reference | Acceptable — string only, no Supabase FK; document in decisions |

---

## Expected outcomes

After full implementation:

- **~80+ pytest tests** (70 existing + ~10 inventory)
- **6 new REST endpoints** under `/api/v1/inventory/`
- **3 PostgreSQL tables** in Supabase (via create_all)
- **Dual-database FastAPI app** — TinyDB auth + Supabase inventory
- **Idempotent seed** via `uv run seed` loading 6 supplies + sample orders on first run

This plan is the execution guide for Milestone 5 backend work. The authoritative requirement details remain in [`milestone5_backend_specs.md`](milestone5_backend_specs.md).
