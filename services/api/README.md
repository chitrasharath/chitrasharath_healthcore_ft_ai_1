# HealthCore API (`services/api`)

FastAPI modular monolith for HealthCore internal tools. Domains include incidents reporting, supplier directory, and JWT authentication with password reset.

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
| `CORS_ORIGINS` | `http://localhost:3004,http://localhost:3005` | Comma-separated allowed origins |
| `EMAIL_API_KEY` | (empty) | Resend API key; when empty, reset links print to stdout |
| `FRONTEND_URL` | `http://localhost:3004` | Base URL for password-reset email links |

## Run

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive docs: http://localhost:8000/docs

## Test

```bash
uv run pytest
```

Tests force `EMAIL_API_KEY=""` so password-reset flows use stdout fallback regardless of local `.env`.

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
| `/api/v1/incidents/analyze` | POST | Yes | Upload incident CSV |
| `/api/v1/incidents/results/export` | GET | Yes | Export last analysis CSV |
| `/api/v1/suppliers` | GET, POST | Yes | List or register suppliers |
| `/api/v1/suppliers/{id}` | GET, DELETE | Yes | Supplier detail; DELETE soft-suspends |
| `/api/v1/suppliers/{id}/rate` | PATCH | Yes | Update monthly rate |
| `/api/v1/suppliers/{id}/status` | PATCH | Yes | Activate or suspend supplier |
| `/api/v1/suppliers/{id}/details` | PATCH | Yes | Update optional fields |

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
