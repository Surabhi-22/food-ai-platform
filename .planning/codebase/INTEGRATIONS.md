# External Integrations

**Date:** 2026-05-12

## Infrastructure Services

### 1. Supabase PostgreSQL
- **Usage:** Primary relational database holding users, orders, menu items, ML forecasts, and analytics.
- **Connection:** Accessed asynchronously via `asyncpg` combined with SQLAlchemy. Configured for Supabase's transaction-mode connection pooling (port 6543) using `prepared_statement_cache_size=0` in connection args.

### 2. Redis
- **Usage:** In-memory key-value store.
- **Purpose 1:** Caching for high-latency analytics queries (e.g., dashboard revenue, top-items) with a standard TTL of 15 minutes. Cache is invalidated on specific mutations (e.g., order confirmation).
- **Purpose 2:** Rate-limiting via sliding window counters (used heavily in `/auth` and `/forecast` endpoints to prevent brute-force and DDoS attacks).

### 3. Vercel
- **Usage:** Frontend hosting infrastructure.
- **Integration Point:** `frontend/vercel.json` dictates edge network configurations, HTTP security headers (CSP, XSS-Protection), and API proxy rewrites routing to the backend.

### 4. Sentry (Configured)
- **Usage:** Application observability and exception tracking.
- **Integration Point:** `backend/app/main.py` conditionally initializes `sentry_sdk` based on environment variables for tracking exceptions and performance profiling.

### 5. OpenAI & Pinecone (Configured)
- **Usage:** Advanced ML features and Retrieval-Augmented Generation (RAG) (planned).
- **Integration Point:** Keys present in Pydantic Settings (`OPENAI_API_KEY`, `PINECONE_API_KEY`).
