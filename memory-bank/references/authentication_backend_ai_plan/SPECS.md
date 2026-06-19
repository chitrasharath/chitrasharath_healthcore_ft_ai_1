# specs.md — AUTH-01: Authentication and Route Protection

## Overview

Add JWT-based authentication to the HealthCore FastAPI backend (`services/api`). The implementation adds two new route groups — `/auth` and `/users` — and protects the `/users` routes behind a `get_current_user` dependency. The existing `/suppliers` and `/incidents` routes are not protected in this milestone but the structure must make it trivial to add protection to them later.

---

## Reference material

- Requirements: `screenshot_content.md` (repo root)
- Existing API entry point: `services/api/app/main.py`
- Existing router wiring: `services/api/app/api/v1/router.py`
- Existing store pattern to follow: `services/api/app/domains/procurement/suppliers/store.py`
- Existing test pattern to follow: `services/api/tests/test_suppliers.py`
- Config: `services/api/app/core/config.py`
- Database: `db.json` (TinyDB, repo root) — all tables share this file

---

## New dependencies (`services/api/pyproject.toml`)

Add to the `dependencies` list:

```toml
"python-jose[cryptography]>=3.3.0",
"passlib[bcrypt]>=1.7.4",
```

---

## Config (`services/api/app/core/config.py`)

Add two new fields to the existing `Settings` class:

```python
secret_key: str = "change-me-before-production"
jwt_expire_minutes: int = 30
```

Both are loaded from `.env` via `pydantic-settings` (already wired). `secret_key` must be overridden via environment variable in any non-local environment — never hardcode a real value.

---

## File layout

All new files follow the same domain structure as `app/domains/procurement/suppliers/`.

```
app/
  core/
    config.py          ← add secret_key, jwt_expire_minutes (existing file)
    dependencies.py    ← NEW: get_current_user dependency
  domains/
    auth/
      __init__.py
      router.py        ← POST /auth/register, POST /auth/login, GET /auth/me
      schemas.py       ← Pydantic request/response models
      service.py       ← register + login logic
      token.py         ← JWT encode/decode helpers
    users/
      __init__.py
      router.py        ← POST /users, GET /users, GET /users/{id}, PUT /users/{id}, DELETE /users/{id}
      service.py       ← user CRUD logic
      store.py         ← TinyDB users table
  api/
    v1/
      router.py        ← wire in auth_router and users_router (existing file, modify)
```

---

## TinyDB user store (`app/domains/users/store.py`)

Use the same `db.json` TinyDB file. Add a new table named `"users"`. Follow the same singleton pattern used in `app/domains/procurement/suppliers/store.py` — share the same `get_db()` function by importing it from the suppliers store, or extract it to `app/core/db.py` to avoid a cross-domain import.

Each user document stored in TinyDB:

```json
{
  "email": "alice@example.com",
  "hashed_password": "$2b$12$...",
  "is_active": true,
  "created_at": "2026-06-18T10:00:00"
}
```

- `id` is the TinyDB `doc_id` — not stored inside the document, injected on read via a `_normalize` helper (same pattern as the suppliers store).
- `created_at` is stored as an ISO 8601 string set at insert time.
- `is_active` defaults to `True` on creation.

### Functions to implement

| Function | Signature | Behaviour |
|---|---|---|
| `insert_user` | `(doc: dict) -> int` | Insert and return `doc_id` |
| `get_by_id` | `(user_id: int) -> dict \| None` | Fetch by `doc_id`, return normalised dict or None |
| `get_by_email` | `(email: str) -> dict \| None` | Search by email field, return normalised dict or None |
| `get_all` | `() -> list[dict]` | Return all users as normalised dicts |
| `update_user` | `(user_id: int, partial: dict) -> dict \| None` | Partial update, return updated doc or None if not found |
| `delete_user` | `(user_id: int) -> bool` | Hard delete by `doc_id`, return True if deleted, False if not found |
| `email_exists` | `(email: str) -> bool` | Guard for duplicate registration |
| `reset_db` | `(path: Path \| None = None) -> None` | For tests — close and re-point the TinyDB singleton |

---

## Pydantic schemas (`app/domains/auth/schemas.py`)

### Internal domain model — never returned by any endpoint

```python
class User(BaseModel):
    id: int
    email: EmailStr
    hashed_password: str
    is_active: bool = True
    created_at: datetime
```

### Request / response schemas

```python
class UserCreate(BaseModel):
    """Used by POST /users and POST /auth/register."""
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class UserUpdate(BaseModel):
    """Used by PUT /users/{id}. All fields optional."""
    email: EmailStr | None = None
    password: str | None = None
    is_active: bool | None = None


class UserLogin(BaseModel):
    """Used by POST /auth/login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Returned by register and login."""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Returned by user endpoints and GET /auth/me."""
    id: int
    email: str
    is_active: bool
    created_at: datetime
    # hashed_password is intentionally never included
```

---

## JWT helpers (`app/domains/auth/token.py`)

Use `from jose import jwt, JWTError`. Algorithm: `HS256`.

```python
def create_access_token(user_id: int) -> str:
    """
    Build payload: {"sub": str(user_id), "exp": utcnow + jwt_expire_minutes}.
    Sign with settings.secret_key using HS256.
    Return the encoded token string.
    """

def decode_access_token(token: str) -> int:
    """
    Decode and verify the token using settings.secret_key.
    Extract "sub", cast to int, return as user_id.
    Raise HTTPException(401, "Could not validate credentials") on any failure
    (expired, invalid signature, missing sub, etc.).
    """
```

---

## `get_current_user` dependency (`app/core/dependencies.py`)

This is the single reusable dependency that protects routes. Any router that needs protection passes it via `dependencies=[Depends(get_current_user)]` at the `include_router()` call — not on individual endpoints.

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    user_id = decode_access_token(token)          # raises 401 on failure
    user = store.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="User not found")
    return user                                    # returns raw dict from store
```

**Note:** `OAuth2PasswordBearer` is used here for FastAPI `/docs` integration (shows the Authorize button). The actual login endpoint accepts a JSON body, not a form — `tokenUrl` is only metadata for the OpenAPI UI.

---

## Service layer

### `app/domains/auth/service.py`

#### `register(body: UserCreate) -> TokenResponse`

1. Check `store.email_exists(body.email)` — if True, raise `DuplicateEmailError`.
2. Hash password: `CryptContext(schemes=["bcrypt"], deprecated="auto").hash(body.password)`.
3. Build doc: `{"email": body.email, "hashed_password": hashed, "is_active": True, "created_at": datetime.utcnow().isoformat()}`.
4. Call `store.insert_user(doc)` to get `user_id`.
5. Call `token.create_access_token(user_id)` and return `TokenResponse`.

#### `login(body: UserLogin) -> TokenResponse`

1. Call `store.get_by_email(body.email)` — if None, raise `InvalidCredentialsError`.
2. `pwd_context.verify(body.password, user["hashed_password"])` — if False, raise `InvalidCredentialsError`.
3. Call `token.create_access_token(user["id"])` and return `TokenResponse`.

**Never reveal whether the email or password was wrong** — both cases raise the same `InvalidCredentialsError` with the same message.

### `app/domains/users/service.py`

#### `create_user(body: UserCreate) -> UserResponse`

Same logic as `auth.service.register` but returns `UserResponse` instead of `TokenResponse`. Delegate to the shared store — do not duplicate the hashing logic. Extract a shared `_hash_password` helper if needed.

#### `list_users() -> list[UserResponse]`

Call `store.get_all()`, return list of `UserResponse`.

#### `get_user(user_id: int) -> UserResponse`

Call `store.get_by_id(user_id)` — if None, raise `UserNotFoundError`.

#### `update_user(user_id: int, body: UserUpdate) -> UserResponse`

1. Call `store.get_by_id(user_id)` — if None, raise `UserNotFoundError`.
2. Build `partial` dict from non-None fields in `body`. If `password` is set, hash it and store as `hashed_password` (never store `password` key).
3. Call `store.update_user(user_id, partial)` and return `UserResponse`.

#### `delete_user(user_id: int) -> None`

Call `store.delete_user(user_id)` — if False, raise `UserNotFoundError`.

### Custom exceptions (define in each service module)

```python
class DuplicateEmailError(Exception): pass
class InvalidCredentialsError(Exception): pass
class UserNotFoundError(Exception): pass
```

---

## Routers

### `app/domains/auth/router.py`

`prefix="/auth"`, `tags=["auth"]`

| Method | Path | Auth required | Returns | Status |
|---|---|---|---|---|
| POST | `/auth/register` | No | `TokenResponse` | 201 |
| POST | `/auth/login` | No | `TokenResponse` | 200 |
| GET | `/auth/me` | Yes (inject `get_current_user` on this endpoint directly) | `UserResponse` | 200 |

Error mapping:
- `DuplicateEmailError` → 422 `{"detail": "Email already registered"}`
- `InvalidCredentialsError` → 401 `{"detail": "Invalid credentials"}`

### `app/domains/users/router.py`

`prefix="/users"`, `tags=["users"]`

| Method | Path | Auth required | Returns | Status |
|---|---|---|---|---|
| POST | `/users` | No | `UserResponse` | 201 |
| GET | `/users` | Yes | `list[UserResponse]` | 200 |
| GET | `/users/{id}` | Yes | `UserResponse` | 200 |
| PUT | `/users/{id}` | Yes | `UserResponse` | 200 |
| DELETE | `/users/{id}` | Yes | `204 No Content` | 204 |

`POST /users` must remain public — do not pass `get_current_user` at the router level. Inject the dependency only on the individual protected endpoints (GET, PUT, DELETE) rather than at router level, so `POST /users` stays open.

For `PUT /users/{id}`: verify `current_user["id"] == user_id`. If not, raise `HTTP 403 "Not authorized"`.

For `DELETE /users/{id}`: currently open to any authenticated user. Add a `# TODO: restrict to admin when RBAC is implemented` comment on the endpoint so it is easy to find and update.

Error mapping:
- `UserNotFoundError` → 404 `{"detail": "User not found"}`

---

## Wiring (`app/api/v1/router.py`)

```python
from fastapi import Depends
from app.domains.auth.router import router as auth_router
from app.domains.users.router import router as users_router

api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)

# To protect additional route groups in future milestones, add:
# from app.core.dependencies import get_current_user
# api_v1_router.include_router(suppliers_router, dependencies=[Depends(get_current_user)])
```

Do not modify the existing `incidents_router` or `suppliers_router` include calls.

---

## Error response reference

| Scenario | HTTP status | `detail` |
|---|---|---|
| Missing or invalid token | 401 | `"Could not validate credentials"` |
| Valid token but user deleted | 401 | `"User not found"` |
| Authenticated user updates another user | 403 | `"Not authorized"` |
| Email already registered | 422 | `"Email already registered"` |
| Wrong email or password | 401 | `"Invalid credentials"` |
| User not found (GET/PUT/DELETE) | 404 | `"User not found"` |

---

## Tests (`services/api/tests/test_auth.py`)

Use the same isolated TinyDB pattern as `tests/test_suppliers.py`: point the store at a `tmp_path` file per test via `reset_db()` in an `autouse` fixture.

Cover the following cases:

### Registration
1. `POST /auth/register` with valid email + password → 201, body contains `access_token`.
2. `POST /auth/register` duplicate email → 422.
3. `POST /auth/register` password under 8 chars → 422.

### Login
4. `POST /auth/login` valid credentials → 200, body contains `access_token`.
5. `POST /auth/login` wrong password → 401.
6. `POST /auth/login` unknown email → 401.

### Auth/me
7. `GET /auth/me` with valid token → 200, returns user profile without `hashed_password`.
8. `GET /auth/me` without token → 401.

### Users CRUD
9. `POST /users` valid → 201, body contains `id`, `email`, `is_active`, `created_at`; no `hashed_password`.
10. `GET /users` with valid token → 200, returns list.
11. `GET /users` without token → 401.
12. `GET /users/{id}` valid token + existing id → 200.
13. `GET /users/{id}` valid token + unknown id → 404.
14. `PUT /users/{id}` owner updates own record → 200.
15. `PUT /users/{id}` authenticated user updates a different user's record → 403.
16. `DELETE /users/{id}` authenticated user → 204.
17. `DELETE /users/{id}` unknown id → 404.

### Token expiry
18. Generate a token with `jwt_expire_minutes` patched to `-1`, call `GET /auth/me` → 401.

---

## What NOT to implement in this milestone

- Role-based access control (RBAC) — deferred. Leave `# TODO` comment on `DELETE /users/{id}`.
- Refresh tokens.
- Session or cookie-based auth.
- Email verification or password reset.
- Protection of `/suppliers` or `/incidents` routes — deferred to a future milestone. The commented-out example in `router.py` shows how to add it.

---

## Future milestone: replace JWT with opaque tokens (HIPAA)

### Why JWT is insufficient for HIPAA

JWT tokens are self-contained and stateless — the server has no record of them. This means:

- A stolen token cannot be revoked before it expires. If a clinician's device is stolen, their session stays active until the expiry window closes.
- HIPAA §164.312(a)(2)(iii) requires automatic logoff and the ability to terminate sessions immediately.
- HIPAA §164.312(b) requires audit controls — with JWT there is no server-side session record to audit.

### What opaque tokens are

Instead of a signed payload the client can decode, the server issues a random string (e.g. `secrets.token_urlsafe(32)`). The token means nothing on its own — it is only valid if it exists in the server's `sessions` table with a non-expired `expires_at`. Every request does a DB lookup to validate it.

This gives:
- **Instant revocation** — delete the session row, the token is dead immediately.
- **No sensitive data in the token** — nothing is encoded or decodable by the client.
- **Audit trail** — every session is a DB record with `created_at`, `last_used_at`, `user_id`, and optionally device/IP metadata.

### How to implement (when ready)

#### 1. New `sessions` table in `db.json`

Add `app/domains/auth/sessions_store.py`. Each session document:

```json
{
  "user_id": 1,
  "token": "3Gv8kLmN...32-char-random-string",
  "expires_at": "2026-06-18T10:30:00",
  "created_at": "2026-06-18T10:00:00",
  "last_used_at": "2026-06-18T10:00:00"
}
```

Functions to implement:

| Function | Signature | Behaviour |
|---|---|---|
| `create_session` | `(user_id: int) -> str` | Generate token via `secrets.token_urlsafe(32)`, insert doc, return token string |
| `get_session` | `(token: str) -> dict \| None` | Look up by token field, return doc or None |
| `delete_session` | `(token: str) -> None` | Hard delete — used for logout |
| `delete_all_for_user` | `(user_id: int) -> None` | Terminate all sessions for a user (e.g. password change, account compromise) |
| `touch_session` | `(token: str) -> None` | Update `last_used_at` to `utcnow()` on each valid request |

#### 2. Remove `app/domains/auth/token.py`

The JWT encode/decode helpers are no longer needed. Delete the file.

#### 3. Remove `python-jose` from `pyproject.toml`

`passlib[bcrypt]` stays — password hashing is unchanged.

#### 4. Update `app/core/dependencies.py`

Replace the JWT decode logic with a session table lookup:

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    token = credentials.credentials
    session = sessions_store.get_session(token)
    if session is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    if datetime.fromisoformat(session["expires_at"]) < datetime.utcnow():
        sessions_store.delete_session(token)
        raise HTTPException(status_code=401, detail="Session expired")
    sessions_store.touch_session(token)
    user = users_store.get_by_id(session["user_id"])
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user
```

#### 5. Update `app/domains/auth/service.py`

- `register()` and `login()` call `sessions_store.create_session(user_id)` instead of `token.create_access_token(user_id)`. The return value is the same `TokenResponse` shape — no change to the API contract.
- Add a `logout()` function that calls `sessions_store.delete_session(token)`. Wire it to a new `POST /auth/logout` endpoint (protected).

#### 6. Add `POST /auth/logout` endpoint

```
POST /api/v1/auth/logout   → 204 No Content   (protected)
```

Calls `sessions_store.delete_session(token)` where `token` is extracted from the `Authorization` header by the dependency. This is the revocation mechanism — call it on user logout, password change, or account suspension.

#### 7. Remove `secret_key` and `jwt_expire_minutes` from `config.py`

Replace with:

```python
session_expire_minutes: int = 30
```

Loaded from `.env` as before.

#### 8. No change to the API contract

The `TokenResponse` shape (`access_token`, `token_type`) is identical. Clients send the token the same way (`Authorization: Bearer <token>`). The switch is entirely server-side — no frontend changes required beyond adding a logout call.

### Config change (`app/core/config.py`)

Remove `secret_key`. Replace `jwt_expire_minutes` with `session_expire_minutes: int = 30`.

### Additional HIPAA considerations for this milestone

- **Audit log** — consider adding a `audit_log` TinyDB table that records every login, logout, and failed login attempt with `user_id`, `action`, `timestamp`, and `ip_address` (extractable from the FastAPI `Request` object).
- **Concurrent session limit** — optionally cap sessions per user (e.g. one active session at a time) by calling `delete_all_for_user()` before `create_session()` on login.
- **Short session window** — 30 minutes of inactivity expiry is reasonable; `touch_session()` resets the clock on each request so active users are not interrupted.
