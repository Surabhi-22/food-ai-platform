# System Architecture — AI Food Demand Forecasting Platform

## 1. Overview

The platform is a **multi-tenant SaaS** designed for Indian food vendors to forecast demand, reduce food waste, and optimize inventory using machine learning. It combines a **FastAPI** backend, **Next.js 14** frontend, an **XGBoost + LSTM ensemble** ML pipeline, and a **RAG-powered AI chatbot**.

---

## 2. High-Level Architecture

```mermaid
graph TB
    subgraph Client["Client Layer"]
        Browser["Browser (Next.js 14)"]
    end

    subgraph Proxy["Reverse Proxy"]
        Nginx["Nginx"]
    end

    subgraph Frontend["Frontend (Vercel)"]
        NextJS["Next.js 14 App Router"]
        API_Routes["API Routes (Auth Proxy)"]
    end

    subgraph Backend["Backend (Railway)"]
        FastAPI["FastAPI (uvicorn)"]
        Auth["JWT Auth Module"]
        CRUD["CRUD APIs"]
        Forecast_API["Forecast API"]
        Chat_API["Chat Streaming API"]
        Scheduler["APScheduler (2 AM UTC)"]
    end

    subgraph ML["ML Pipeline"]
        Preprocess["Preprocessing"]
        Features["Feature Engineering"]
        XGBoost["XGBoost Regressor"]
        LSTM["LSTM (TensorFlow)"]
        Ensemble["Ensemble (0.6 XGB + 0.4 LSTM)"]
        KMeans["K-Means Clustering"]
    end

    subgraph External["External Services"]
        OpenWeather["OpenWeatherMap API"]
        OpenAI["OpenAI GPT-4o"]
        Pinecone["Pinecone Vector DB"]
        Sentry["Sentry Error Tracking"]
    end

    subgraph Data["Data Layer"]
        Postgres["PostgreSQL (Supabase)"]
        Redis["Redis (Cache + Rate Limit)"]
    end

    Browser --> Nginx --> NextJS
    NextJS --> API_Routes --> FastAPI
    FastAPI --> Auth
    FastAPI --> CRUD --> Postgres
    FastAPI --> Forecast_API --> Redis
    FastAPI --> Chat_API --> OpenAI
    Chat_API --> Pinecone
    Scheduler --> Preprocess --> Features
    Features --> OpenWeather
    Features --> XGBoost
    Features --> LSTM
    XGBoost --> Ensemble
    LSTM --> Ensemble
    Ensemble --> Postgres
    Preprocess --> KMeans
    FastAPI --> Sentry
```

---

## 3. Data Flow Diagram

```mermaid
flowchart LR
    subgraph Ingestion["Data Ingestion"]
        Orders["Vendor Orders"]
        Menu["Menu Items"]
        Weather["Weather API"]
        Holidays["Holiday Calendar"]
    end

    subgraph Processing["Processing Pipeline"]
        Clean["Clean & Fill Gaps"]
        Normalize["MinMax Normalize"]
        FE["Feature Engineering\n(28 features)"]
    end

    subgraph Training["Model Training"]
        Split["TimeSeriesSplit CV"]
        XGB["XGBoost\n(5-fold CV)"]
        LSTM_T["LSTM\n(14-day sequences)"]
        Eval["Evaluate\nRMSE, MAE, MAPE"]
    end

    subgraph Serving["Serving"]
        Cache["Redis Cache\n(1h TTL)"]
        API["Forecast API"]
        Dashboard["Dashboard UI"]
        Chatbot["RAG Chatbot"]
    end

    Orders --> Clean --> Normalize --> FE
    Menu --> FE
    Weather --> FE
    Holidays --> FE
    FE --> Split --> XGB --> Eval
    Split --> LSTM_T --> Eval
    Eval --> Cache --> API --> Dashboard
    API --> Chatbot
```

---

## 4. ML Pipeline Flowchart

```mermaid
flowchart TD
    A["Scheduler Trigger\n(Daily 2:00 AM UTC)"] --> B["Load Raw Orders\n(90 days)"]
    B --> C["Preprocessing\n• Forward-fill gaps\n• MinMax normalization"]
    C --> D["Feature Engineering\n• 7 temporal\n• 3 lag\n• 4 rolling\n• 5 weather\n• 9 event"]
    D --> E{"Sufficient\ndata?"}
    E -->|"< 30 days"| F["Skip Training\nUse Last Model"]
    E -->|">= 30 days"| G["K-Means Clustering\n(k=3)"]
    G --> H["XGBoost Training\n5-fold TimeSeriesSplit"]
    G --> I["LSTM Training\n14-day sequences"]
    H --> J["Ensemble Prediction\n0.6 × XGB + 0.4 × LSTM"]
    I --> J
    J --> K["Generate 3-Day Forecast\n• Predicted quantity\n• Revenue / Profit\n• Confidence intervals (95%)\n• Inventory = qty × 1.15"]
    K --> L["Store in PostgreSQL\n+ Invalidate Redis Cache"]
    L --> M["Log Metrics\nto ml_run_logs"]
    M --> N{"MAPE < 25%?"}
    N -->|Yes| O["✓ Success"]
    N -->|No| P["⚠ Sentry Alert"]
```

---

## 5. Technology Choices & Justification

| Layer | Technology | Justification |
|---|---|---|
| **Backend** | FastAPI | Async support, auto-generated OpenAPI docs, Pydantic validation, 10x faster than Flask (Tiangolo, 2023) |
| **Frontend** | Next.js 14 (App Router) | Server-side rendering for SEO, React Server Components, streaming support, Vercel-native deployment |
| **Database** | PostgreSQL (Supabase) | ACID compliance, JSON support, Row-Level Security, managed hosting with automatic backups |
| **Cache** | Redis | Sub-millisecond reads, pub/sub for real-time, rate limiting with atomic INCR, forecast caching |
| **ML — Tabular** | XGBoost | State-of-the-art for tabular data (Chen & Guestrin, 2016), handles mixed features, built-in feature importance |
| **ML — Sequential** | LSTM | Captures long-term temporal dependencies in demand sequences (Hochreiter & Schmidhuber, 1997) |
| **ML — Clustering** | K-Means | Simple, interpretable demand segmentation (MacQueen, 1967), enables cluster-specific strategies |
| **AI Chatbot** | GPT-4o + RAG | Retrieval-Augmented Generation prevents hallucination on vendor-specific data (Lewis et al., 2020) |
| **Vector DB** | Pinecone | Managed vector search, namespace isolation per vendor, cosine similarity at scale |
| **Weather** | OpenWeatherMap | One Call API 3.0 for forecast + historical data, well-documented, free tier sufficient |
| **Deployment** | Docker + Railway + Vercel | Container isolation, Railway for backend auto-scaling, Vercel for edge-optimized frontend |
| **CI/CD** | GitHub Actions | Native GitHub integration, matrix builds, artifact caching, secret management |
| **Monitoring** | Sentry | Real-time error tracking, performance monitoring, release tracking |

---

## 6. Security Architecture

| Control | Implementation |
|---|---|
| **Authentication** | JWT (access + refresh tokens), bcrypt password hashing, HttpOnly cookies |
| **Multi-Tenancy** | vendor_id in every SQL query + `assert_vendor_ownership()` defense-in-depth |
| **Rate Limiting** | Redis-backed: 100 req/min per IP, 60 req/min per vendor token |
| **Headers** | X-Content-Type-Options, X-Frame-Options, HSTS, Referrer-Policy |
| **CORS** | Restricted to configured production domains only |
| **SQL Injection** | All queries via SQLAlchemy ORM (parameterized queries) |

---

## 7. Database Schema (Key Tables)

| Table | Key Columns | Purpose |
|---|---|---|
| `vendors` | id, email, hashed_password, business_name | Multi-tenant vendor accounts |
| `menu_items` | id, vendor_id, name, category, price, cost_% | Menu catalog per vendor |
| `orders` | id, vendor_id, customer_name, status, total | Order tracking |
| `order_items` | id, order_id, menu_item_id, quantity, price | Line items |
| `forecasts` | id, vendor_id, menu_item_id, forecast_date, qty, revenue | ML predictions |
| `ml_run_logs` | id, vendor_id, run_date, status, metrics | Training audit trail |
| `chat_sessions` | id, vendor_id, messages (JSONB) | RAG conversation history |
