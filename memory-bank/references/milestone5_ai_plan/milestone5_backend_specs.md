# Milestone 5 — Backend Inventory Management: Implementation Spec

> **Branch:** `feature/milestone5` (off `main`)
> **Working directory:** `services/api/`

---

## 1. Project Overview

**HealthCore** is an outpatient healthcare services company operating 12 clinics across the USA (Texas, Florida, Georgia) and the UK (London, Manchester). This milestone adds a centralised **medical supply inventory management system** to the existing FastAPI backend.

The system tracks what supplies are available across clinics — syringes, PPE, wound care materials, diagnostic test kits, and medications. Until now, each location managed stock in local spreadsheets with no central visibility. Running out of PPE mid-shift or using expired supplies creates clinical risk.

### What this milestone builds

A set of REST API endpoints under `/inventory` that allow:
- Registering medical supply items in a central catalogue.
- Logging **supply deliveries** (vendor shipments received at a clinic) that increase stock.
- Logging **supply consumptions** (clinical use or expiry waste events) that decrease stock.
- Querying products with real-time computed stock levels.
- Querying a combined order history across deliveries and consumptions.

### Dual-database architecture

The application maintains **two simultaneous database connections**:

| Database | Purpose | Used by |
|----------|---------|---------|
| **TinyDB** (existing) | Users, authentication, JWT tokens | `get_db()` — unchanged from prior milestones |
| **Supabase (PostgreSQL)** (new) | Medical supplies, deliveries, consumptions | `get_supabase_db()` — new dependency |

No user data is replicated in Supabase. Order records store a `user_uuid` string referencing the TinyDB user who created them.

### Stakeholder context

> **James Osei (CTO) — Jira ticket HCR-0188:** "We need a medical supply inventory API as the foundation for the clinical operations dashboard. Supply entries are deliveries from vendors. Supply exits are clinical consumptions logged by clinic staff. Stock is always the net of entries minus exits — direct modification is not allowed. All routes under `/inventory`. User UUIDs come from TinyDB. Claire has confirmed: supply inventory data is operational, not PHI — no HIPAA barriers on this API, but access must be authenticated."

---

## 2. Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| **Framework** | FastAPI | Existing — app defined in `app/main.py` |
| **ORM** | SQLModel | Combines SQLAlchemy's ORM engine with Pydantic's type system. Do NOT use raw SQLAlchemy directly. |
| **Relational DB** | Supabase (hosted PostgreSQL) | New for this milestone. Connection via `DATABASE_URL` env var. |
| **Document DB** | TinyDB | Existing — stores users and auth tokens. Unchanged. |
| **Schemas** | Pydantic v2 (`BaseModel`) | Request/response schemas separate from ORM models. |
| **Settings** | pydantic-settings (`BaseSettings`) | Existing — loads from `.env` file. |
| **Auth** | JWT via python-jose | Existing — `get_current_user` dependency in `app/core/dependencies.py`. |
| **Password hashing** | passlib + bcrypt | Existing — unchanged. |
| **Testing** | pytest + httpx (`TestClient`) | Existing test infrastructure in `tests/`. |
| **Python** | >= 3.12 | As specified in `pyproject.toml`. |

---

## 3. Business Constraints Enforced in API

These constraints come from the operations team's RFP and the CTO brief. They are non-negotiable and must be enforced at the API/model level — not just documented.

### 3.1 Stock is computed, never stored

`current_stock` for any supply is always: `SUM(SupplyDelivery.quantity) − SUM(SupplyConsumption.quantity)`. There is no `current_stock` column in the database. It is computed on read and included in response schemas only.

### 3.2 No direct stock mutation

There is no endpoint to set or update stock directly. The only way to change inventory is by registering an order — a `SupplyDelivery` (inbound) that adds stock, or a `SupplyConsumption` (outbound) that removes it.

### 3.3 Negative stock prevention

A `SupplyConsumption` that would result in negative stock must be rejected **before** the record is persisted. Return HTTP 400 with message: `"Insufficient stock for supply '{name}'. Available: {available}, requested: {quantity}."`

### 3.4 Order traceability

Every order (delivery or consumption) must record the `user_uuid` of the authenticated user who created it. All order creation endpoints require authentication.

### 3.5 Consumption type validation

`consumption_type` on `SupplyConsumption` must be either `"clinical_use"` (used in patient care) or `"expiry_waste"` (expired and discarded). Any other value is rejected with a validation error.

### 3.6 US and UK supplies coexist

Supplies from both jurisdictions live in the same table. The `country` field (`"US"` or `"UK"`) identifies the regulatory jurisdiction and must be present in both the ORM model and response schema.

### 3.7 Clinic IDs are plain integers

Clinic IDs range from 1–12 (9 US clinics in Texas/Florida/Georgia, 3 UK clinics in London/Manchester). They are stored as integers on delivery and consumption records — not foreign keys in this milestone.

---

## 4. Dependencies

### 4.1 Existing dependencies (do not remove)

From `pyproject.toml`:

```
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
pandas>=2.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-multipart>=0.0.9
tinydb>=4.8.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
bcrypt>=4.0.0,<4.1
email-validator>=2.0.0
resend>=2.0.0
```

Dev dependencies:

```
httpx>=0.27.0
pytest>=8.0.0
```

### 4.2 New dependencies to add

Add these to `pyproject.toml` under `[project] dependencies`:

```
"sqlmodel>=0.0.22",
"psycopg2-binary>=2.9.0",
```

`sqlmodel` provides the ORM layer (SQLModel classes, engine, session). `psycopg2-binary` is the PostgreSQL driver needed to connect to Supabase.

---

## 5. Development Workflow

### 5.1 Branch setup

```bash
git checkout main && git pull
git checkout -b feature/milestone5
```

All work happens on `feature/milestone5`. Do not commit directly to `main`.

### 5.2 Install dependencies

From `services/api/`:

```bash
pip install -e ".[dev]"
```

Or to install just the new packages:

```bash
pip install sqlmodel psycopg2-binary
```

### 5.3 Environment setup

Create `services/api/.env` with:

```env
SECRET_KEY=<your-secret>
JWT_EXPIRE_MINUTES=30
DATABASE_URL=postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
```

The `.env` file is already gitignored by the root `.gitignore`.

### 5.4 Running the API server

From `services/api/`:

```bash
uvicorn app.main:app --reload --port 8000
```

On first startup with a valid `DATABASE_URL`, the `on_startup` event creates the tables in Supabase via `SQLModel.metadata.create_all()`.

### 5.5 Seeding data

After the tables are created:

```bash
python -m app.seed
```

This runs the existing supplier seed and the new inventory seed function.

### 5.6 Running tests

```bash
pytest tests/ -v
```

Inventory tests use an SQLite override so they do NOT require a live Supabase connection. Existing auth/supplier/incident tests continue to work unchanged.

### 5.7 Verifying endpoints

With the server running, use the FastAPI interactive docs:

```
http://localhost:8000/docs
```

All inventory endpoints appear under the `/api/v1/inventory/` prefix. POST endpoints require a Bearer token — register a user first via `/api/v1/auth/register`, then use the returned token.

---

## 6. File Structure

All new files go under `services/api/app/domains/inventory/`. Do NOT modify any existing auth, users, suppliers, or incidents code except where explicitly noted below.

```
services/api/app/
├── main.py                              # MODIFY: add startup event, import inventory router
├── core/
│   ├── config.py                        # MODIFY: add database_url field
│   ├── db.py                            # MODIFY: add SQLModel engine + get_supabase_db
│   └── dependencies.py                  # NO CHANGE (get_current_user stays as-is)
├── api/v1/
│   └── router.py                        # MODIFY: include inventory router
└── domains/
    └── inventory/                       # NEW directory
        ├── __init__.py                  # NEW (empty)
        ├── models.py                    # NEW: SQLModel ORM models
        ├── schemas.py                   # NEW: Pydantic request/response schemas
        ├── router.py                    # NEW: APIRouter(prefix="/inventory")
        └── seed.py                      # NEW: seed data function
```

---

## 7. Configuration Changes

### 7.1 `app/core/config.py`

Add one field to the `Settings` class:

```python
database_url: str = ""
```

No other changes. The existing fields (`secret_key`, `jwt_expire_minutes`, etc.) remain untouched.

### 7.2 `app/core/db.py`

Add the SQLModel engine **alongside** the existing TinyDB setup. Do NOT remove or modify the existing `get_db()` or `reset_db()` functions.

Add at the bottom of the file:

```python
from sqlmodel import Session, SQLModel, create_engine
from app.core.config import settings

supabase_engine = create_engine(settings.database_url, echo=False)

def get_supabase_db():
    with Session(supabase_engine) as session:
        yield session
```

**Key rules:**
- `get_supabase_db` is a generator that yields a `Session` per request — used via `Depends(get_supabase_db)`.
- No global `Session` variable.
- The engine must only be created if `database_url` is set (to avoid breaking existing tests that don't set it). Wrap the engine creation:

```python
supabase_engine = None
if settings.database_url:
    supabase_engine = create_engine(settings.database_url, echo=False)

def get_supabase_db():
    with Session(supabase_engine) as session:
        yield session
```

### 7.3 `app/main.py`

Add a startup event (or lifespan) that calls `SQLModel.metadata.create_all(supabase_engine)` to create tables in Supabase on app start. Also include the inventory router.

Add these imports and the startup event:

```python
from sqlmodel import SQLModel
from app.core.db import supabase_engine

@app.on_event("startup")
def on_startup():
    if supabase_engine:
        SQLModel.metadata.create_all(supabase_engine)
```

Include the inventory router (see section 10 for how to register it).

### 7.4 `app/api/v1/router.py`

Add the inventory router import and include it. The inventory router has its own prefix `/inventory`, and some routes are public while others require auth — auth is applied per-endpoint inside the inventory router, NOT at the include level.

```python
from app.domains.inventory.router import router as inventory_router

api_v1_router.include_router(inventory_router)
```

---

## 8. ORM Models — `app/domains/inventory/models.py`

Use `SQLModel` with `table=True`. Three models, using the HealthCore entity names exactly.

### 8.1 `MedicalSupply`

```python
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field

class MedicalSupply(SQLModel, table=True):
    __tablename__ = "medical_supply"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    sku: str
    category: str      # "ppe", "wound_care", "diagnostics", "medications", "consumables"
    unit: str           # "box", "unit", "pack", "vial"
    country: str        # "US" or "UK"
```

**Rules:**
- `id` is auto-increment primary key.
- NO `current_stock` column. Stock is always computed.
- All fields are required (no defaults except `id`).

### 8.2 `SupplyDelivery` (Inbound Order)

```python
class SupplyDelivery(SQLModel, table=True):
    __tablename__ = "supply_delivery"

    id: Optional[int] = Field(default=None, primary_key=True)
    supply_id: int = Field(foreign_key="medical_supply.id")
    quantity: int
    vendor_name: str
    clinic_id: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_uuid: str
```

### 8.3 `SupplyConsumption` (Outbound Order)

```python
class SupplyConsumption(SQLModel, table=True):
    __tablename__ = "supply_consumption"

    id: Optional[int] = Field(default=None, primary_key=True)
    supply_id: int = Field(foreign_key="medical_supply.id")
    quantity: int
    consumption_type: str   # "clinical_use" or "expiry_waste"
    clinic_id: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_uuid: str
```

**Key rules for all models:**
- Foreign keys use `Field(foreign_key="medical_supply.id")` — the table name, not the class name.
- `user_uuid` is `str` — stores `str(user["id"])` from TinyDB (the existing user store uses integer doc_ids, not UUIDs; convert to string for storage).
- `created_at` auto-sets to UTC now on creation.

---

## 9. Pydantic Schemas — `app/domains/inventory/schemas.py`

Separate file from models. These are pure Pydantic `BaseModel` classes (NOT `SQLModel`). Never return a raw ORM model from an endpoint.

### 9.1 MedicalSupply Schemas

```python
from pydantic import BaseModel
from datetime import datetime

class MedicalSupplyCreate(BaseModel):
    name: str
    sku: str
    category: str
    unit: str
    country: str

class MedicalSupplyRead(BaseModel):
    id: int
    name: str
    sku: str
    category: str
    unit: str
    country: str
    current_stock: int    # computed, not stored

    model_config = {"from_attributes": True}
```

### 9.2 SupplyDelivery Schemas

```python
class SupplyDeliveryCreate(BaseModel):
    supply_id: int
    quantity: int
    vendor_name: str
    clinic_id: int

class SupplyDeliveryRead(BaseModel):
    id: int
    supply_id: int
    quantity: int
    vendor_name: str
    clinic_id: int
    created_at: datetime
    user_uuid: str

    model_config = {"from_attributes": True}
```

### 9.3 SupplyConsumption Schemas

```python
class SupplyConsumptionCreate(BaseModel):
    supply_id: int
    quantity: int
    consumption_type: str   # validate: must be "clinical_use" or "expiry_waste"
    clinic_id: int

class SupplyConsumptionRead(BaseModel):
    id: int
    supply_id: int
    quantity: int
    consumption_type: str
    clinic_id: int
    created_at: datetime
    user_uuid: str

    model_config = {"from_attributes": True}
```

Add a field validator on `SupplyConsumptionCreate.consumption_type`:

```python
from pydantic import field_validator

@field_validator("consumption_type")
@classmethod
def validate_consumption_type(cls, v: str) -> str:
    allowed = ("clinical_use", "expiry_waste")
    if v not in allowed:
        raise ValueError(f"consumption_type must be one of {allowed}")
    return v
```

### 9.4 Combined Order Schema (for `GET /inventory/orders`)

```python
class OrderRead(BaseModel):
    id: int
    order_type: str          # "inbound" or "outbound"
    supply_id: int
    supply_name: str         # from the related MedicalSupply
    quantity: int
    user_uuid: str
    created_at: datetime
    # Include type-specific fields:
    vendor_name: str | None = None        # only for inbound
    consumption_type: str | None = None   # only for outbound
    clinic_id: int
```

---

## 10. Inventory Router — `app/domains/inventory/router.py`

### 10.1 Router Setup

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func

from app.core.db import get_supabase_db
from app.core.dependencies import get_current_user
from app.domains.inventory.models import MedicalSupply, SupplyDelivery, SupplyConsumption
from app.domains.inventory.schemas import (
    MedicalSupplyCreate, MedicalSupplyRead,
    SupplyDeliveryCreate, SupplyDeliveryRead,
    SupplyConsumptionCreate, SupplyConsumptionRead,
    OrderRead,
)

router = APIRouter(prefix="/inventory")
```

### 10.2 Stock Computation Helper

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

This function is reused in every endpoint that returns product data.

### 10.3 Endpoints

| Method | Path | Auth | Handler Details |
|--------|------|------|-----------------|
| `GET` | `/inventory/products` | No | Query all `MedicalSupply` rows, compute `current_stock` for each, return list of `MedicalSupplyRead`. |
| `POST` | `/inventory/products` | Yes | Accept `MedicalSupplyCreate`, create `MedicalSupply` row, return `MedicalSupplyRead` with `current_stock=0`. |
| `GET` | `/inventory/products/{id}` | No | Get single `MedicalSupply` by id, compute stock, return `MedicalSupplyRead`. Return 404 if not found. |
| `POST` | `/inventory/orders/inbound` | Yes | Accept `SupplyDeliveryCreate`. Validate that `supply_id` exists (404 if not). Create `SupplyDelivery` with `user_uuid=str(current_user["id"])`. Return `SupplyDeliveryRead`. |
| `POST` | `/inventory/orders/outbound` | Yes | Accept `SupplyConsumptionCreate`. Validate `supply_id` exists (404). Compute current stock. If `quantity > available`, return HTTP 400: `"Insufficient stock for supply '{name}'. Available: {available}, requested: {quantity}."`. Otherwise create `SupplyConsumption` with `user_uuid=str(current_user["id"])`. Return `SupplyConsumptionRead`. |
| `GET` | `/inventory/orders` | No | Return all deliveries and consumptions combined as list of `OrderRead`. Load product data eagerly (avoid N+1). |

**Auth pattern:** Protected endpoints use `current_user: dict = Depends(get_current_user)` as a parameter. The user dict from TinyDB has an `"id"` key (integer). Store `str(current_user["id"])` in `user_uuid`.

**Error responses:**
- Product not found: `HTTPException(status_code=404, detail="Product not found")`
- Insufficient stock: `HTTPException(status_code=400, detail="Insufficient stock for supply '{name}'. Available: {available}, requested: {quantity}.")`

### 10.4 N+1 Avoidance for `GET /inventory/orders`

For the combined orders endpoint, do NOT loop over orders and query the product for each one. Instead:

Option A: Query all deliveries and consumptions, collect all unique `supply_id` values, batch-fetch all products in one query, then build the response in Python.

Option B: Use a joined query.

Either approach is acceptable. The key constraint is: no per-order product query inside a loop.

---

## 11. Seed Data — `app/domains/inventory/seed.py`

Create a seed function that inserts the required data into Supabase. This function should be idempotent (skip if data already exists).

### 11.1 MedicalSupply seed data (6 records)

| name | sku | category | unit | country |
|------|-----|----------|------|---------|
| Nitrile gloves (box of 100) | HCR-PPE-001 | ppe | box | US |
| Surgical mask (pack of 50) | HCR-PPE-002 | ppe | pack | UK |
| Adhesive wound dressing | HCR-WND-001 | wound_care | box | US |
| Rapid strep test kit | HCR-DIAG-001 | diagnostics | unit | US |
| Blood glucose test strips (50) | HCR-DIAG-002 | diagnostics | box | UK |
| 0.9% Saline solution 500ml | HCR-MED-001 | medications | vial | US |

### 11.2 SupplyDelivery seed data (minimum 4 records)

- At least 2 deliveries for `HCR-PPE-001` (Nitrile gloves) with different quantities.
- Use vendor names: `"MedLine Industries"`, `"Cardinal Health UK"`, `"Bound Tree Medical"`.
- Mix `clinic_id` values across US (1–9) and UK (10–12) clinics.
- Use `user_uuid` = `"1"` (the first seeded TinyDB user, as a string).

Example deliveries:

| supply (by sku) | quantity | vendor_name | clinic_id | user_uuid |
|-----------------|----------|-------------|-----------|-----------|
| HCR-PPE-001 | 100 | MedLine Industries | 1 | "1" |
| HCR-PPE-001 | 50 | Bound Tree Medical | 3 | "1" |
| HCR-PPE-002 | 200 | Cardinal Health UK | 10 | "1" |
| HCR-DIAG-001 | 30 | MedLine Industries | 5 | "1" |

### 11.3 SupplyConsumption seed data (minimum 3 records)

- At least one `"clinical_use"` and one `"expiry_waste"`.
- Quantities must NOT exceed seeded delivery totals for that supply.
- Use `user_uuid` = `"1"`.

Example consumptions:

| supply (by sku) | quantity | consumption_type | clinic_id | user_uuid |
|-----------------|----------|------------------|-----------|-----------|
| HCR-PPE-001 | 20 | clinical_use | 1 | "1" |
| HCR-PPE-001 | 5 | expiry_waste | 3 | "1" |
| HCR-PPE-002 | 10 | clinical_use | 10 | "1" |

### 11.4 Integration

Add a `seed_inventory()` function. Wire it so it can be called either:
- As part of the existing `seed.py` main function, OR
- Via a separate endpoint or CLI command.

The simplest approach: add a call to `seed_inventory()` inside `app/seed.py`'s `main()` function, importing the inventory seed function.

The seed function must:
1. Get a session from `get_supabase_db` (or create one directly from `supabase_engine`).
2. Check if supplies already exist (by SKU) before inserting — skip duplicates.
3. Insert deliveries and consumptions only if the related supplies were just created (to avoid duplicate seed runs creating extra orders).

---

## 12. Tests — `services/api/tests/test_inventory.py`

### 12.1 Test setup

In `conftest.py`, add the `DATABASE_URL` env var setup:

```python
os.environ.setdefault("DATABASE_URL", "")
```

For tests that hit inventory endpoints, you have two options:
- **Option A (recommended):** Use an in-memory SQLite database for tests by overriding `get_supabase_db` via FastAPI dependency overrides. This avoids requiring a real Supabase connection for CI.
- **Option B:** Use a test Supabase database.

### 12.2 Test fixtures (Option A — SQLite override)

```python
from sqlmodel import SQLModel, Session, create_engine
from app.core.db import get_supabase_db
from app.main import app

test_engine = create_engine("sqlite:///test_inventory.db")

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
```

### 12.3 Required test cases

Write tests covering:

1. **`POST /api/v1/inventory/products`** — creates a product, returns it with `current_stock: 0`. Requires auth header.
2. **`GET /api/v1/inventory/products`** — returns list with `current_stock` computed correctly.
3. **`GET /api/v1/inventory/products/{id}`** — returns single product with stock. Returns 404 for missing id.
4. **`POST /api/v1/inventory/orders/inbound`** — creates a delivery, stock increases. Requires auth.
5. **`POST /api/v1/inventory/orders/outbound`** — creates a consumption, stock decreases. Requires auth.
6. **Outbound rejection** — attempting to consume more than available stock returns HTTP 400 with the expected message format.
7. **Invalid consumption_type** — posting with `consumption_type: "stolen"` returns HTTP 422 validation error.
8. **`GET /api/v1/inventory/orders`** — returns combined list of deliveries and consumptions with `order_type`, `supply_name`, etc.
9. **Auth required** — POST endpoints without auth token return HTTP 401.
10. **Stock computation correctness** — after multiple inbound and outbound orders, `current_stock` reflects the correct net.

**Auth in tests:** Use the same pattern as existing tests. Register a user via `POST /api/v1/auth/register`, extract the token, pass it as `Authorization: Bearer {token}` header. Refer to `tests/auth_helpers.py` for the existing auth helper pattern.

---

## 13. Business Rules Summary

These are non-negotiable and the evaluator will test them:

1. **`current_stock` is computed, never stored.** Formula: `SUM(SupplyDelivery.quantity) - SUM(SupplyConsumption.quantity)` for each supply.
2. **New products start at zero stock.** Stock only increases via `POST /inventory/orders/inbound`.
3. **Outbound orders that would cause negative stock are rejected** with HTTP 400 and message: `"Insufficient stock for supply '{name}'. Available: {available}, requested: {quantity}."`
4. **`consumption_type` must be `"clinical_use"` or `"expiry_waste"`.** Invalid values get a validation error.
5. **No user table in Supabase.** `user_uuid` is a plain string storing `str(current_user["id"])`.
6. **`country` field** must be present on `MedicalSupply` model and response schema.
7. **`clinic_id`** must be present on both `SupplyDelivery` and `SupplyConsumption`.
8. **All inventory routes under `/inventory`** prefix via dedicated `APIRouter`.
9. **ORM models and Pydantic schemas in separate files** (`models.py` vs `schemas.py`).
10. **Never return raw ORM objects** from endpoints — always map to Pydantic schema.
11. **Two DB connections active:** TinyDB for auth (`get_db`), SQLModel/Supabase for inventory (`get_supabase_db`).
12. **`get_supabase_db` injected per request** via `Depends()` — no global session variable.

---

## 14. Acceptance Criteria Checklist

After implementation, verify all of these pass:

- [ ] `feature/milestone5` branch exists and all changes are committed there.
- [ ] `DATABASE_URL` is in `.env` (not hardcoded). `.env` is gitignored.
- [ ] `pyproject.toml` includes `sqlmodel` and `psycopg2-binary`.
- [ ] `app/core/db.py` has both TinyDB (`get_db`) and SQLModel (`get_supabase_db`) setup.
- [ ] `app/core/config.py` has `database_url` field.
- [ ] `app/main.py` calls `SQLModel.metadata.create_all()` on startup.
- [ ] `app/domains/inventory/models.py` defines `MedicalSupply`, `SupplyDelivery`, `SupplyConsumption` using `SQLModel, table=True`.
- [ ] `MedicalSupply` has NO `current_stock` column.
- [ ] Foreign keys: `SupplyDelivery.supply_id` and `SupplyConsumption.supply_id` → `medical_supply.id`.
- [ ] `app/domains/inventory/schemas.py` has separate Pydantic schemas with `MedicalSupplyRead.current_stock`.
- [ ] `app/domains/inventory/router.py` uses `APIRouter(prefix="/inventory")`.
- [ ] All 6 endpoints implemented and functional under `/api/v1/inventory/...`.
- [ ] `GET /api/v1/inventory/products` returns products with correct computed `current_stock`.
- [ ] `POST /api/v1/inventory/orders/outbound` with excessive quantity returns HTTP 400.
- [ ] `POST /api/v1/inventory/orders/outbound` with invalid `consumption_type` returns validation error.
- [ ] Auth-protected endpoints return 401 without a valid token.
- [ ] `user_uuid` on orders matches the authenticated user's TinyDB id (as string).
- [ ] Seed data is present (6 supplies, 4+ deliveries, 3+ consumptions).
- [ ] Tests in `tests/test_inventory.py` pass.
- [ ] No N+1 queries in `GET /inventory/orders`.
- [ ] Entity names match HealthCore context exactly (`MedicalSupply`, `SupplyDelivery`, `SupplyConsumption`).

---

## 15. What NOT to Change

- Do NOT modify any files under `app/domains/auth/`, `app/domains/users/`, `app/domains/procurement/`, or `app/domains/reporting/`.
- Do NOT modify `app/core/dependencies.py` (the `get_current_user` function).
- Do NOT replicate a users table in Supabase.
- Do NOT add a stored `current_stock` column.
- Do NOT use raw SQLAlchemy — use SQLModel only.
- Do NOT create a global `Session` variable.
