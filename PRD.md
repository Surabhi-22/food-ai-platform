# Product Requirements Document (PRD)
## AI-Powered Vendor Food Demand Forecasting & Analytics Platform

**Version:** 1.0.0  
**Date:** 2026-05-11  
**Status:** Draft  
**Owner:** Product Team

---

## 1. Executive Summary

This platform is an AI-powered SaaS system that helps food vendors make data-driven decisions by combining real-time order management, machine learning-based demand forecasting, analytics dashboards, and a RAG-based AI chatbot. The core objective is to reduce food wastage, optimize inventory planning, and improve vendor profit margins through accurate demand predictions.

---

## 2. Problem Statement

Food vendors currently operate on intuition and historical guesswork, leading to:
- Significant food wastage due to overproduction
- Revenue loss from stockouts and unmet demand
- Inability to plan inventory around external factors (weather, festivals, events)
- No actionable insights from accumulated order data

---

## 3. Goals & Success Metrics

| Goal | KPI | Target |
|---|---|---|
| Reduce food wastage | % reduction in unsold inventory | ≥ 20% in 3 months |
| Improve forecast accuracy | MAPE on 3-day forecasts | ≤ 15% |
| Increase vendor revenue | Avg. monthly profit per vendor | +10% QoQ |
| Drive platform adoption | Monthly Active Vendors | 500 in 6 months |
| Chatbot engagement | % queries resolved without escalation | ≥ 85% |

---

## 4. User Personas

### 4.1 Admin
- Manages platform settings, vendor onboarding, and system health
- Reviews global analytics and usage metrics
- Manages ML model versioning and retraining schedules

### 4.2 Vendor
- Primary user: food business operator
- Needs: demand forecasts, inventory recommendations, profit analysis
- Uses: dashboard, chatbot, order management module
- Pain point: no data-backed planning tools today

### 4.3 Customer
- Places orders through the vendor-facing order portal
- Acts as the primary data source for the ML pipeline
- Not a direct consumer of analytics

---

## 5. Core Features & Requirements

### 5.1 Authentication & Multi-Tenancy
- **FR-01:** JWT-based login for Admins and Vendors
- **FR-02:** Role-based access control (RBAC) — Admin, Vendor, Customer
- **FR-03:** Each vendor's data is strictly isolated (row-level security via Supabase)
- **FR-04:** Password reset, email verification flows

### 5.2 Order Management
- **FR-05:** Vendors can create and manage menu items (name, price, category)
- **FR-06:** Customers can browse menus and place orders
- **FR-07:** Vendors can confirm, reject, or update order statuses
- **FR-08:** All orders are persisted to PostgreSQL and trigger the ML pipeline on confirmation
- **FR-09:** Real-time order status updates via WebSockets or Supabase Realtime

### 5.3 ML Pipeline
- **FR-10:** Automated data preprocessing on new order ingestion (missing value imputation, normalization)
- **FR-11:** Feature engineering — day-of-week, hour-of-day, rolling 7-day averages, weather features, festival flags
- **FR-12:** K-Means clustering to segment menu items by demand pattern
- **FR-13:** XGBoost model for tabular/structured demand forecasting
- **FR-14:** LSTM model for sequential time-series forecasting
- **FR-15:** Model evaluation using RMSE, MAE, and MAPE; store metrics per run
- **FR-16:** Models serialized and versioned (MLflow or local artifact store)
- **FR-17:** Background retraining triggered on schedule (daily) or on data threshold (e.g., 100 new orders)
- **FR-18:** Prediction API exposes next-3-day demand per item, revenue, and inventory quantity

### 5.4 AI Prediction Engine
- **FR-19:** Per-item demand forecast for the next 3 days
- **FR-20:** Revenue forecast based on demand predictions × menu prices
- **FR-21:** Profit estimation with configurable COGS percentage
- **FR-22:** Inventory requirement calculation with safety stock buffer
- **FR-23:** Confidence intervals displayed alongside predictions

### 5.5 Analytics Dashboard
- **FR-24:** Demand forecasting chart (line/bar) per food item, per day
- **FR-25:** Revenue trend chart (actual vs predicted)
- **FR-26:** Top-selling items leaderboard
- **FR-27:** Inventory insights panel with reorder alerts
- **FR-28:** Profit margin analysis by item and category
- **FR-29:** Real-time sales counter updated via WebSocket
- **FR-30:** Date-range filter for all historical analytics

### 5.6 AI Chatbot (RAG-Based)
- **FR-31:** Vendor-specific vector embeddings stored in Pinecone
- **FR-32:** On query, perform semantic search on vendor's data (orders, forecasts, menu)
- **FR-33:** Augment retrieved context into OpenAI GPT prompt for grounded response
- **FR-34:** Chatbot strictly answers from vendor's own data — no cross-tenant leakage
- **FR-35:** Chat history retained per session; optionally persisted per vendor
- **FR-36:** Example supported queries: "What should I prepare tomorrow?", "Which items are overstocked?", "What was my best-selling item last week?"

### 5.7 External Data Integrations
- **FR-37:** Weather API integration (OpenWeatherMap) — temperature, rainfall as forecast features
- **FR-38:** Festival/public holiday calendar ingestion (static config + optional API)

---

## 6. Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Performance** | Dashboard loads in < 2 seconds; Prediction API responds in < 500ms |
| **Scalability** | Backend horizontally scalable; ML workers run as independent background services |
| **Security** | All data encrypted at rest and in transit (TLS); row-level security per vendor |
| **Availability** | 99.5% uptime SLA |
| **Observability** | Structured logging; error tracking via Sentry; API latency metrics |
| **Compliance** | GDPR-ready: data export and deletion per vendor on request |

---

## 7. System Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js / Vercel)                 │
│   Dashboard  │  Order Portal  │  Analytics  │  Chatbot UI          │
└──────────────────────────┬─────────────────────────────────────────┘
                           │ REST + WebSocket
┌──────────────────────────▼─────────────────────────────────────────┐
│                        BACKEND (FastAPI / Railway)                  │
│  Auth API  │  Order API  │  Prediction API  │  Chatbot API          │
└────────┬───────────┬──────────────┬──────────────┬─────────────────┘
         │           │              │              │
    ┌────▼────┐ ┌────▼─────┐ ┌─────▼──────┐ ┌────▼────────┐
    │Supabase │ │ ML Worker │ │  OpenAI    │ │  Pinecone   │
    │(Postgres│ │(XGBoost / │ │  GPT API   │ │ Vector DB   │
    │+ Auth)  │ │  LSTM)    │ │            │ │             │
    └─────────┘ └──────────┘ └────────────┘ └─────────────┘
```

---

## 8. Data Models (High-Level)

### Vendor
`id, name, email, password_hash, business_name, created_at`

### MenuItem
`id, vendor_id, name, category, price, cogs_percentage, is_active`

### Order
`id, vendor_id, customer_id, status, total_amount, created_at`

### OrderItem
`id, order_id, menu_item_id, quantity, unit_price`

### Forecast
`id, vendor_id, menu_item_id, forecast_date, predicted_quantity, predicted_revenue, confidence_lower, confidence_upper, model_version, created_at`

### ChatSession
`id, vendor_id, messages (JSONB), created_at, updated_at`

---

## 9. API Design (Summary)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/login` | Vendor / Admin login |
| POST | `/auth/register` | New vendor registration |
| GET | `/menu/{vendor_id}` | List menu items |
| POST | `/orders` | Place an order |
| PATCH | `/orders/{id}/status` | Update order status |
| GET | `/forecasts/{vendor_id}` | Get 3-day demand forecasts |
| POST | `/chat` | Send message to RAG chatbot |
| GET | `/analytics/{vendor_id}/revenue` | Revenue trend data |
| GET | `/analytics/{vendor_id}/top-items` | Top-selling items |
| POST | `/ml/retrain/{vendor_id}` | Trigger manual retraining |

---

## 10. Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, Tailwind CSS, Recharts, ShadCN UI |
| Backend | FastAPI (Python 3.11+) |
| Database | PostgreSQL via Supabase |
| Auth | Supabase Auth + JWT |
| ML | XGBoost, TensorFlow/Keras (LSTM), scikit-learn |
| Vector DB | Pinecone |
| LLM | OpenAI GPT-4o |
| Deployment | Vercel (frontend), Railway/Render (backend), Supabase (DB) |
| Background Jobs | APScheduler / Celery + Redis |
| Observability | Sentry, structured JSON logging |

---

## 11. Milestones & Timeline

| Phase | Deliverable | Duration |
|---|---|---|
| Phase 1 | Auth, Order Management, DB schema | Week 1–2 |
| Phase 2 | ML Pipeline (XGBoost + LSTM) + Prediction API | Week 3–4 |
| Phase 3 | Analytics Dashboard (Next.js) | Week 5–6 |
| Phase 4 | RAG Chatbot integration | Week 7 |
| Phase 5 | External data (weather, festivals) + retraining scheduler | Week 8 |
| Phase 6 | Testing, performance tuning, deployment | Week 9–10 |

---

## 12. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Insufficient vendor data for ML | High (early stage) | Seed with synthetic data; fallback to moving average |
| OpenAI API cost overrun | Medium | Rate limit chatbot; cache frequent queries |
| ML retraining latency blocking API | Medium | Run retraining as background async worker |
| Cross-tenant data leakage in chatbot | Low | Enforce vendor_id filter at vector search layer |
| Supabase downtime | Low | Enable connection pooling; add retry logic |

---

## 13. Out of Scope (v1.0)

- Mobile app (iOS / Android)
- Multi-language support
- Payment gateway integration
- Supplier/procurement management
- Customer loyalty programs
