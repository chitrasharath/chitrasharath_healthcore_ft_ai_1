# Evaluation Criteria — AUTH-02 (Forgot/Reset Password)

## What We Will Evaluate

- [ ] `POST /auth/forgot-password` sends a real email containing the reset link when called with a registered address.
- [ ] `POST /auth/forgot-password` returns `200` even when the address is not registered — no information is leaked.
- [ ] The reset token expires after the configured window and cannot be used after expiry.
- [ ] `POST /auth/reset-password` updates the password and invalidates the token on success.
- [ ] `POST /auth/reset-password` returns `400` for expired or already-used tokens.
- [ ] `/forgot-password` shows a confirmation message after submission regardless of the result.
- [ ] `/reset-password` reads the token from the URL, submits the form, and redirects to `/login` on success.
- [ ] `/reset-password` shows a clear error with a link back to `/forgot-password` when the token is invalid or expired.
- [ ] The `/login` page has a visible "Forgot your password?" link.
- [ ] No API keys are hardcoded — all secrets are loaded from environment variables.

---

# Evaluation Criteria — AUTH-03 (Login, Registration & Protected Views)

## What We Will Evaluate

- [ ] Login and registration forms work end-to-end: the token is stored after a successful call.
- [ ] Protected views redirect to `/login` when there is no valid token in storage.
- [ ] The public website (Milestone 1) continues to work without any authentication check.
- [ ] The profile view displays and updates the current user's data using the token.
- [ ] Logout removes the token and redirects correctly.
- [ ] A `401` response from any protected API call clears the session and redirects to `/login`.
