# Testing Patterns

**Date:** 2026-05-12

## Backend Testing Strategy

- **Framework**: Built around `pytest` and `pytest-asyncio` for asynchronous endpoint testing.
- **Client Mocking**: FastAPI's `TestClient` and `AsyncClient` from `httpx` are intended for integration testing endpoints.
- **Database Mocking**: Unit tests should patch the SQLAlchemy `AsyncSession` to avoid hitting live Postgres, or use a dedicated temporary SQLite/Postgres container for true integration tests.

## Frontend Testing Strategy

- **Static Analysis**: TypeScript compiler and ESLint (`eslint-config-next`) ensure strict syntactic constraints.
- **Component Validation**: (Future implementation needed) Jest / React Testing Library for verifying isolated component rendering.

## CI/CD integration
- (Future implementation needed) GitHub Actions for automated unit testing on PR creation.
