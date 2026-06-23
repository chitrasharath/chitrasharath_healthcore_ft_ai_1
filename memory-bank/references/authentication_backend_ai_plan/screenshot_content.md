# Securing the API: Authentication and Route Restriction in FastAPI

## 🎯 Your Challenge

📌 You are building on your own fork of the company's monorepo selected at the beginning.

Your company's API is growing. You've built endpoints that serve data to the frontend, query the database, and process records — but right now, anyone who knows a URL can call any of them. Before the platform goes into its next phase, the CTO has made it clear: no route that modifies or exposes sensitive data should be reachable without a valid session.

Your tech lead has just dropped a ticket in your queue:

**AUTH-01 — Implement authentication and route protection**

The API currently has no authentication layer. This task covers:
- A users module with full CRUD (create, read, update, delete).
- A login endpoint that validates credentials and returns a signed JWT token.
- A reusable `get_current_user` dependency that decodes the token and identifies the caller.
- Application of that dependency to all routes that should not be publicly accessible.

Use `OAuth2PasswordBearer` from FastAPI and `python-jose` for token signing. Passwords must be hashed — never stored or compared in plain text. The token should carry the user's ID at minimum and expire after a configurable window.

All auth-related routes must live under `/auth`. User management routes under `/users`.

This is a security concern, not a feature: the work you do here protects everything that was built before it and everything that comes after. Do it right.

**Note:** Once you protect your routes, some frontend calls may stop working temporarily — that's expected. The frontend will be updated to send the token in subsequent work. For now, focus on securing the API to prevent data leaks and unauthorized access.

---

## Complementary knowledge: how JWT authentication works in FastAPI

If you haven't implemented JWT auth before, here's the mental model: when a user logs in, the server signs a small JSON payload (the "claims") using a secret key and returns the result as a token string. On subsequent requests, the client sends that token in the `Authorization` header. The server decodes it — if the signature is valid and the token hasn't expired, the request proceeds; if not, it gets a 401.

In FastAPI, this flow is implemented as a dependency. You write a function that extracts the token from the request, validates it, and returns the user object. Any route that declares that function as a dependency will automatically require authentication.

---

## 🌱 How to Start the Project

This project is an extension of your existing transversal project API. Do not create a new repository. Work inside your company's current backend codebase.

1. Open your existing project in Codespaces or clone it locally.
2. Create a new branch for this feature: `git checkout -b feature/auth`
3. Install the required packages: `pip install python-jose[cryptography] passlib[bcrypt]`
4. Add them to your `requirements.txt`.

---

## 💻 What You Need to Do

### User model and CRUD

- Create a `User` model in the database with: `id`, `email`, `hashed_password`, `is_active`, `created_at`
- Implement a service layer with functions to: get user by id, get user by email, create user, update user, delete user
- Expose these as REST endpoints under `/users`:
  - `POST /users` — register a new user (hash the password before storing)
  - `GET /users` — list all users (protected)
  - `GET /users/{id}` — get a single user (protected)
  - `PUT /users/{id}` — update a user (protected, only the user themselves or an admin)
  - `DELETE /users/{id}` — delete a user (protected, admin only)

### Authentication endpoints

- Implement `POST /auth/register` — accepts email and password, validates credentials, returns a JWT access token. The token should be placed in the response immediately.
- Implement `POST /auth/login` — accepts email and password, validates credentials, returns a JWT access token.
- Implement `GET /auth/me` (protected) — returns the profile of the currently authenticated user.

### Token and dependency

- Create a `get_current_user` dependency that extracts the `Authorization: Bearer <token>` header, decodes the JWT, retrieves the user from the database, and returns it. If anything fails, return HTTP 401.
- Set token expiry as an environment variable (`JWT_EXPIRE_MINUTES`). Store the signing secret in `.env`; never hardcode it.

### Route protection

- Apply `get_current_user` as a dependency to every route that should be protected. At minimum, protect all `/users` endpoints except `POST /users` and `POST /auth/login`.
- Return `HTTP 401` for unauthenticated and `HTTP 403` when a user tries a route they don't have permission for.

### Testing

- Verify the full flow manually using the FastAPI interactive docs (`/docs`): register → login → copy token → use token on a protected route.
- Confirm that calling a protected route without a token returns 401.
- Confirm that calling a protected route with an expired or malformed token returns 401.

---

⚠️ **IMPORTANT:** Do not use session-based or cookie-based authentication. This project implements stateless JWT auth only.

⚠️ **IMPORTANT:** Never store plain-text passwords. Use `passlib` with the `bcrypt` scheme for all password operations.
