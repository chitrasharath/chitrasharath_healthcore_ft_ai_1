# Evaluation Criteria — AUTH-01

## What We Will Evaluate

- [ ] User CRUD is fully implemented and reachable via the API.
- [ ] Passwords are hashed at creation and compared correctly at login — plain text never touches the database.
- [ ] Login endpoint returns a valid, signed JWT token.
- [ ] `get_current_user` dependency correctly decodes the token and identifies the user.
- [ ] Protected routes return `401` when called without a valid token.
- [ ] Token expiry and signing secret are read from environment variables, not hardcoded.
- [ ] Auth routes are under `/auth` and user routes are under `/users` — clean, consistent structure.
- [ ] The existing routes of the project continue to work (no regressions).

> **Note:** Role-based access control (admin vs. regular user) is not required for this delivery, though it is a valid extension if time allows.
