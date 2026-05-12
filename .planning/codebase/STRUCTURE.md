# Directory Structure

**Date:** 2026-05-12

## Top-Level Layout

The repository is structured as a monolithic repository containing multiple distinct operational services:

- `backend/` — The FastAPI Python application.
- `frontend/` — The Next.js React application.
- `docs/` — Project documentation and guides.
- `PRD.md` / `README.md` — Global project context and product requirements.
- `.planning/` — GSD framework context memory and codebase maps.

## Backend Structure (`backend/`)
- `app/` — Core application code.
  - `api/` — HTTP routing, request parsing, response generation (e.g., `orders.py`, `auth.py`).
  - `core/` — System-wide configuration (`config.py`), security utilities (`security.py`), error definitions (`exceptions.py`), and Redis connections (`redis.py`).
  - `crud/` — Database interaction layer separating business logic from routing (e.g., `crud_orders.py`).
  - `db/` — Database connection pooling and session management (`session.py`).
  - `models/` — SQLAlchemy ORM definitions mapping directly to tables (e.g., `order.py`, `vendor.py`).
  - `schemas/` — Pydantic models for strict data validation (e.g., `order.py`).
  - `ml/` — Machine learning pipeline integration.
- `alembic/` — Database migration scripts and environment config.
- `Dockerfile` — Instructions for building the containerized deployment environment.

## Frontend Structure (`frontend/`)
- `src/` — Next.js application source.
  - `app/` — Next.js App Router definitions.
  - `components/` — Reusable React components (UI library and features).
  - `lib/` — Frontend utilities and Axios API configurations.
- `public/` — Static assets served by Next.js.
- `vercel.json` — Edge routing and security headers for Vercel deployment.
- `next.config.ts` — Framework configuration.
