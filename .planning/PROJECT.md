# Food AI Demand Platform

## What This Is
An AI-powered SaaS system that helps food vendors make data-driven decisions by combining real-time order management, machine learning-based demand forecasting, analytics dashboards, and a RAG-based AI chatbot. It aims to reduce food wastage and optimize inventory planning.

## Core Value
Accurate, data-backed demand forecasting that directly translates into reduced food waste and improved vendor profit margins.

## Requirements

### Validated
<!-- Shipped and confirmed valuable based on current codebase -->
- ✓ JWT-based secure authentication and vendor registration with rate limiting
- ✓ Core data models (Vendor, MenuItem, Order, Forecast) built on PostgreSQL/Supabase
- ✓ Order management API with status transitions
- ✓ Redis-backed analytics endpoints with sub-10ms cache retrieval
- ✓ Base Next.js frontend with secure Vercel edge deployment configuration
- ✓ XGBoost/LSTM machine learning pipelines for demand prediction (Phase 1)
- ✓ Next.js Analytics Dashboard UI with Recharts (Phase 2)
- ✓ Pinecone & OpenAI RAG-based Vendor Chatbot (Phase 3)
- ✓ OpenWeatherMap API and Festival Calendar integrations (Phase 4)
- ✓ APScheduler background worker for model retraining (Phase 1)

### Active (v1.1 - Testing & Stability)
<!-- Current scope. Building toward these. -->
- [x] Implement Pytest suite for FastAPI backend (unit tests for routes, models, CRUD)
- [ ] Implement Jest and React Testing Library for Next.js frontend UI components
- [x] Setup GitHub Actions CI/CD pipeline to run tests automatically on push
- [ ] Audit and patch remaining SonarQube / ESLint / MyPy warnings (Partial: Backend fixed)

### Out of Scope
<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->
- Mobile app (iOS / Android) — Web platform covers 95% of vendor needs for v1.0
- Multi-language support — MVP targeted at single locale
- Payment gateway integration — Platform focuses on data/predictions, not financial processing
- Supplier/procurement management — Too much scope for MVP
- Customer loyalty programs — Distraction from core ML forecasting value

## Context
- **Ecosystem:** FastAPI backend with Supabase Postgres. Next.js frontend deployed to Vercel.
- **Constraints:** High performance requirements (sub 500ms API, sub 2s dashboard load). Strict tenant data isolation via Row-Level Security in Supabase to ensure vendors never see competitors' data.
- **State:** The core CRUD, authentication, and caching layers are production-ready. The system now needs the actual ML predictive intelligence and the frontend visualization UI built out.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use Redis for analytics caching | Aggregation queries were too slow for real-time dashboards | ✓ Good |
| Invalidate cache on order confirmation | Ensures dashboard remains real-time without polling the DB constantly | ✓ Good |
| Multi-tenant single DB | Easier to manage than database-per-vendor. Managed via Supabase RLS | — Pending |

---
*Last updated: 2026-05-12 after initialization*
