# Areas of Concern

**Date:** 2026-05-12

## Technical Debt & Fragility

### 1. Model Retraining Synchronization
The ML pipeline executes asynchronously when an order is confirmed (`app/api/orders.py`). Triggering an expensive XGBoost retraining job on *every* order confirmation may overwhelm the system under heavy load.
**Recommendation**: Transition to a batched, cron-based queue system (e.g., nightly retrains via APScheduler or Celery) rather than synchronous trigger logic.

### 2. Dependency on Supabase Transaction Pooling
The backend utilizes PgBouncer connection pooling via Supabase in transaction mode (port 6543). This strictly requires `prepared_statement_cache_size=0`. If this configuration is accidentally removed from `session.py` or Alembic, the system will instantly crash with prepared statement errors under load.

### 3. Missing Frontend Component Testing
While the backend has a robust validation layer (Pydantic), the Next.js frontend currently relies purely on TypeScript for structural safety. The lack of Jest / React Testing Library unit tests makes UI refactors inherently risky.

### 4. Caching Expiration Bounds
Analytics responses are cached in Redis for 15 minutes (`ANALYTICS_CACHE_TTL`). While explicit invalidation exists for `Order` mutations, changes to `MenuItem` (e.g., price changes) do not invalidate the analytics cache, potentially leading to temporarily stale revenue displays.
