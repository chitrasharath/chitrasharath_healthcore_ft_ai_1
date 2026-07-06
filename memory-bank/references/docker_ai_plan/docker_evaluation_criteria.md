# ✅ What We Will Evaluate

- [ ] `docker compose up` from the repository root starts the full platform without errors and without additional configuration steps.
- [ ] Code changes on the host are reflected in the browser without rebuilding the image (bind mounts working on both services).
- [ ] The UI service starts both Next.js applications on separate ports (3000 and 3001) from a single container.
- [ ] Services communicate internally by Docker service name, not by `localhost` or hardcoded IP.
- [ ] No secrets, API keys, or passwords are hardcoded in any `Dockerfile` or in `docker-compose.yml`.
- [ ] The `.env` file is in `.gitignore` and does not appear in the commit history.
- [ ] `.dockerignore` files exist in `/uis/` and in `/services/`.
