# HealthCore API (`services/api`)

FastAPI modular monolith for HealthCore internal tools. Domains include incidents reporting, supplier directory, and JWT authentication.

## Setup

```bash
cd services/api
uv sync --extra dev
cp .example.env .env
```

`SECRET_KEY` and `JWT_EXPIRE_MINUTES` are **required** — set them in `.env` (see `.example.env` for template values). Override `SECRET_KEY` in any non-local environment.

## Run

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive docs: http://localhost:8000/docs

## Test

```bash
uv run pytest
```

## Authentication (AUTH-01)

Passwords are bcrypt-hashed. Protected routes require `Authorization: Bearer <token>`.

Plan: `memory-bank/references/authentication_backend_ai_plan/IMPLEMENTATION_PLAN.md`

### Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/auth/register` | POST | No | Register; returns JWT (`201`) |
| `/api/v1/auth/login` | POST | No | Login; returns JWT (`200`) |
| `/api/v1/auth/me` | GET | Yes | Current user profile |
| `/api/v1/users` | POST | No | Create user (no token returned) |
| `/api/v1/users` | GET | Yes | List all users |
| `/api/v1/users/{id}` | GET | Yes | Get user by id |
| `/api/v1/users/{id}` | PUT | Yes | Update own record only (`403` otherwise) |
| `/api/v1/users/{id}` | DELETE | Yes | Delete user (`204`) |

`/api/v1/suppliers` and `/api/v1/incidents` remain **unprotected** in this milestone.

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
```

Use `/docs` → **Authorize** to paste the token for interactive testing.
