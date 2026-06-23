# AUTH-03 — Password Reset Flow

Right now, a user who forgets their password has no way to recover their account. And beyond that: in any production system, periodically changing passwords is a basic security practice. Your platform has no mechanism for either.

## The Ticket

The platform needs a full password reset mechanism. This covers both the API and the frontend:

### Backend

- `POST /auth/forgot-password` — receives an email, validates the user exists, generates a signed short-lived reset token, and sends a reset link to the user's email address.
- `POST /auth/reset-password` — receives the reset token and a new password, validates the token (signature + expiry), hashes the new password, and updates the user record. The token must be invalidated after use.

### Frontend

- `/forgot-password` — form where the user enters their email. Always shows a confirmation message after submission, regardless of whether the address exists, to prevent user enumeration.
- `/reset-password` — form where the user sets a new password. Reads the reset token from the URL query string and submits it to the API alongside the new password. On success, redirects to `/login`.

### Email Delivery

Choose one of the following services and integrate it:
- **Resend**
- **SendGrid (Twilio)**

**Why only these two?** For this exercise, Resend and SendGrid are the practical choices: you can complete the reset flow in development **without a custom domain** (Resend via their onboarding sender; SendGrid via trial/sandbox or a verified single sender — check their current docs). Alternatives such as Mailgun or MailerSend typically require you to **verify your own domain in DNS** before sending to arbitrary recipients, which blocks many students during the project.

Both offer a free tier sufficient for development. API keys must be stored in environment variables — never hardcoded.

---

## Complementary Knowledge: How a Password Reset Flow Works

The flow has three steps and two separate moments in time:

1. **Request** — the user submits their email. The server generates a reset token (a signed JWT or a random string stored in the database), builds a reset URL containing that token (`/reset-password?token=<token>`), and sends it to the user's email via a transactional email service.

2. **Reset** — the user clicks the link, lands on the `/reset-password` page, enters a new password, and submits. The frontend sends the token (read from the URL) and the new password to the API. The server validates the token — if the signature is valid and it hasn't expired — updates the password, and invalidates the token so it can't be reused.

3. **Confirmation** — the user is redirected to `/login` and can sign in with the new password.

**Why always show a confirmation message?** If the form shows "email not found" for addresses that don't exist, an attacker can use that to enumerate which emails are registered. Always responding with "if that address is in our system, you'll receive a link" prevents this.

**Token expiry matters.** A reset token should have a short lifespan — 15 to 60 minutes is standard. After it's used or after it expires, it should be unusable. If you use a JWT, encode the expiry in the payload. If you use a random string stored in the database, store the expiry timestamp alongside it.

---

## What You Need to Do

### Backend

- `POST /auth/forgot-password` — accepts `{ email }`. If the user exists, generate a reset token with a short expiry (15–60 minutes) and send an email containing the reset link. Always return a `200` response regardless of whether the email was found.
- `POST /auth/reset-password` — accepts `{ token, new_password }`. Validate the token (signature and expiry). If valid, hash the new password, update the user record, and invalidate the token. Return `400` for invalid or expired tokens.
- Integrate one transactional email service (Resend or SendGrid) to send the reset email. The email must include the reset link and be readable on mobile.
- Store the email service API key in an environment variable. Document which variable name to set in your `README` or `.env.example`.

### Frontend

- `/forgot-password` — email input form. On submit, call `POST /auth/forgot-password` and display a confirmation message ("If that address is registered, you'll receive a link shortly"). The form should be disabled after submission to prevent duplicate requests.
- `/reset-password` — new password form with a confirmation field. Read the `token` from the URL query string. On submit, call `POST /auth/reset-password`. On success, redirect to `/login` with a success message. On failure (expired or invalid token), show a clear error and a link back to `/forgot-password`.
- Add a "Forgot your password?" link on the `/login` page pointing to `/forgot-password`.

### Security

- Reset tokens must expire and be invalidated after use — a token cannot be used twice.
- The `/forgot-password` endpoint must always return `200`, never reveal whether an email is registered.
- API keys must never appear in the codebase — use environment variables exclusively.

---

## Going Further (optional)

These are not evaluated but are valid extensions if time allows:

- **HTML email template** — send a styled email instead of a plain-text link.
- **Rate limiting** — limit the number of reset requests per email address per hour to prevent abuse.
- **Audit log** — record each password reset event (timestamp, IP address) in the database.
