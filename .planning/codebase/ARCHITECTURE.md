# System Architecture

**Date:** 2026-05-12

## High-Level Architecture

The Food AI Demand Platform utilizes a monolithic client-server architecture decoupled into a Next.js React Frontend and a FastAPI Python Backend, communicating over REST HTTP APIs.

### Backend Data Flow (FastAPI)
The backend follows a strict multi-layer architectural pattern:
1. **Routers (`app/api/`)**: Handle HTTP orchestration, dependency injection (`Depends`), and response serialization. They contain NO raw SQL or business logic.
2. **Services / CRUD (`app/crud/`)**: Encapsulate all SQLAlchemy database interactions, queries, and mutations.
3. **Schemas (`app/schemas/`)**: Pydantic models acting as strict boundaries for incoming request validation and outgoing response formatting.
4. **Models (`app/models/`)**: Declarative SQLAlchemy ORM models mapping Python classes to Supabase Postgres tables.

### Frontend Data Flow (Next.js)
1. **Pages (`src/app/` or `src/pages/`)**: Define routing and high-level layout.
2. **Components (`src/components/`)**: Modular, reusable UI components built on Radix UI and customized via Tailwind.
3. **API Integration**: Uses Axios to communicate with the FastAPI backend. Proxy rewrites in `vercel.json` mask the backend domain behind `/api/v1/`.

## Key Abstractions

- **OAuth2PasswordBearer**: Standardized JWT token extraction and validation, integrated seamlessly with FastAPI's OpenAPI specification.
- **Cache Invalidation Lifecycle**: Analytics are aggressively cached in Redis to drop latency below 10ms. Mutations in the system (like confirming an `Order` in `app/api/orders.py`) trigger targeted cache invalidation hooks (`cache_invalidate_pattern`) ensuring dashboard coherency.
- **Background Task Execution**: Fast HTTP response times are preserved by offloading heavy ML predictions and model retraining to asynchronous processes or FastAPI `BackgroundTasks`.
