# `docs` folder

This folder holds **cross-cutting documentation** for the monorepo: architecture guides, technical decisions, conventions, processes, and any material shared across applications, pipelines, agents, and workflows.

- **Main purpose**: provide a single place for “global” project documentation (not tied to one app or agent only).
- **Recommendation**: organize docs by topic (architecture, deployment, data, security, observability, etc.) and keep links from each component’s README to these guides.

## Architecture

- **[architecture_proposal.md](./architecture_proposal.md)** — Target-state FastAPI backend (`services/api`), domain model, Supabase, Auth/JWT, and frontend boundaries.

> _Spanish version: [README.es.md](./README.es.md)._
