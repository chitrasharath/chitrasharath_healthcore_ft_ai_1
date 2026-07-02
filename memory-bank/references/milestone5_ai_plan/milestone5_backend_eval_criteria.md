# ✅ What We Will Evaluate

- [ ] Two database connections are demonstrably present and used correctly: TinyDB for auth and user lookups; Supabase (SQLModel) for all inventory entities.
- [ ] All inventory endpoints are grouped under `/inventory` via a dedicated `APIRouter`.
- [ ] SQLModel ORM models correctly declare FK relationships: `InboundOrder.product_id` and `OutboundOrder.product_id` reference the `Product` table.
- [ ] `current_stock` is computed from orders — no endpoint allows direct modification of a stock field on the Product.
- [ ] An outbound order that exceeds available stock is rejected with `HTTP 400` before any write occurs.
- [ ] Every order stores the `user_uuid` of the authenticated creator (sourced from TinyDB).
- [ ] ORM models (`models.py`) and Pydantic schemas (`schemas.py`) are in separate files and are structurally different — no endpoint returns a raw SQLModel object.
- [ ] The SQLModel session is injected per request via `Depends()` — no global session exists in the codebase.
- [ ] All connection parameters live in `.env`; `.env` is listed in `.gitignore`.
- [ ] Entity names and field names match the student's CONTEXT.md specification.
