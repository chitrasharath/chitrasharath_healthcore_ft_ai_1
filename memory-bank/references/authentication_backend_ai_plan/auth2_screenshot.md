# Connecting the Lock: Authentication Flows in the Frontend

## Your Challenge

> You are building on **your own fork** of the company's monorepo selected at the beginning of the course — not on a new repository.

In the previous delivery you secured the API. Protected routes now return `401` to anyone without a valid session — including your own frontend. It's time to close that loop.

Your tech lead has opened the next ticket:

### AUTH-02 — Authentication flows and protected views in the frontend

The API now requires a JWT token on protected routes. This task covers the frontend side of that contract:

- **Login and registration views** — forms that call the API, receive the token, and store it correctly.
- **Account management views** — profile page and password change form.
- **Route protection** — any view that requires a session must redirect unauthenticated users to login. This applies to all applications in the monorepo **except the public website (Milestone 1)**, which remains fully public.

The token must be stored in `localStorage` and attached to every protected API call via the `Authorization: Bearer` header. On logout, the token is removed and the user is redirected to login.

Do not build a separate authentication app. Integrate these flows into the existing Next.js applications inside your monorepo.

---

## Complementary knowledge: the frontend side of JWT

Once the API returns a token at login, the frontend's job is: store it, send it, and react to its absence. The standard pattern in Next.js is:

1. **Store** the token in `localStorage` after a successful login response.
2. **Read** the token on every protected API call and set it in the `Authorization` header: `Bearer <token>`.
3. **Protect routes** — in Next.js App Router this is handled with a middleware or a layout-level check: if there is no token, redirect to `/login`.
4. **Clear** the token on logout and redirect.

> **Note:** The temporary frontend breakage from the previous delivery ends here. By the end of this project, all protected views should be working end-to-end with real authentication.

---

## What You Need to Do

### Authentication views

- `/login` — email and password form. On success: store the token in `localStorage`, redirect to the main authenticated view. On failure: show a clear error message.
- `/register` — registration form. On success: store the token, redirect. On failure: show field-level validation errors.

### Account management views

- `/account/profile` — displays the current user's data (name, email). Allows editing name. Calls `PUT /users/{id}` with the token in the header.
- `/account/change-password` — form with current password, new password, and confirmation. Validates that the new password and confirmation match before calling the API.

### Route protection

- Identify every view in your Next.js applications (excluding the public website) that requires an authenticated session.
- Implement a protection mechanism — middleware, layout guard, or a custom hook — that checks for the token in `localStorage` and redirects to `/login` if it is absent or invalid.
- Ensure the public website (Milestone 1) is entirely unaffected — no token check, no redirect.

### Token lifecycle

- On login and registration: store the token in `localStorage`.
- On every protected API call: read the token and attach it as `Authorization: Bearer <token>`.
- On logout: remove the token from `localStorage` and redirect to `/login`.
- If a protected API call returns `401`: clear the token and redirect to `/login`.
