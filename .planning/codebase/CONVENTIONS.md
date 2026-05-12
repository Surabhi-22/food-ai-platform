# Coding Conventions

**Date:** 2026-05-12

## Python / FastAPI Conventions

1. **Dependency Injection**: Heavy reliance on FastAPI's `Depends()` system.
   - Authentication context is injected via `Depends(get_current_vendor)` in `deps.py`.
   - Database sessions are injected via `Depends(get_db)`.
   - Pagination and complex filtering use dependency schemas (e.g., `OrderFilterParams`).
2. **Separation of Concerns**:
   - Routes (`app/api/`) MUST NOT contain raw `select()` or `add()` database statements. All ORM operations reside in `app/crud/`.
   - Complex data transformations should happen in the CRUD layer or through Pydantic model methods.
3. **Async Everything**: 
   - Strict use of `async`/`await` for all I/O bound operations, utilizing `AsyncSession` and `asyncpg`.
4. **Error Handling**:
   - Never return raw HTTP 500 exceptions to the client.
   - Use custom exceptions inheriting from `AppException` in `app/core/exceptions.py` (e.g., `NotFoundError`, `AuthenticationError`). These are caught by a global error handler to produce consistent JSON formats.
5. **Database Transaction Boundaries**:
   - `get_db` dependency does NOT auto-commit.
   - Route handlers or CRUD methods must explicitly call `await db.commit()` at the conclusion of a successful mutation to ensure predictable transaction lifetimes.

## TypeScript / Next.js Conventions

1. **Strict Typing**: Leverage TypeScript interfaces for API responses and component props.
2. **Component Libraries**: 
   - Primitive interactive components are sourced from Radix UI for accessibility.
   - Styles are composed using Tailwind CSS classes, dynamically merged using `tailwind-merge` and `clsx`.
3. **Form Handling**: Complex forms (e.g., login, registration) are managed by `react-hook-form` and validated entirely client-side using `zod` schemas.
