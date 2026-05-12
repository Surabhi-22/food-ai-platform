# 🍽️ AI-Powered Vendor Food Demand Forecasting & Analytics Platform

> An end-to-end SaaS platform combining real-time order management, ML-powered demand forecasting, analytics dashboards, and a RAG-based AI chatbot — built to reduce food wastage and maximize vendor profits.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
  - [Environment Variables](#environment-variables)
- [ML Pipeline](#ml-pipeline)
- [API Reference](#api-reference)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

---

## 🌐 Overview

This platform enables food vendors to:
- Accept and manage customer orders
- Automatically train XGBoost and LSTM models on their sales data
- Receive 3-day ahead demand, revenue, and inventory forecasts
- Visualize trends via a real-time analytics dashboard
- Query their own business data through a RAG-powered AI chatbot

The system creates a **continuous learning loop**: every new order enriches the ML models, which produce more accurate predictions, which in turn power the dashboard and chatbot.

---

## ✨ Features

| Module | Highlights |
|---|---|
| 🔐 Auth | JWT authentication, RBAC (Admin / Vendor / Customer), Supabase Auth |
| 🛒 Order Management | Menu CRUD, order placement, real-time status updates via WebSocket |
| 🤖 ML Pipeline | XGBoost + LSTM, K-Means clustering, automated daily retraining, RMSE/MAE/MAPE metrics |
| 📈 Prediction Engine | 3-day demand forecast, revenue estimate, profit projection, inventory requirements |
| 📊 Analytics Dashboard | Demand charts, revenue trends, top-selling items, inventory alerts |
| 💬 AI Chatbot (RAG) | Vendor-scoped vector search (Pinecone) + GPT-4o grounded responses |
| 🌤️ External Data | Weather API, festival/holiday calendar as ML features |
| 🚀 Deployment | Vercel + Railway + Supabase + Pinecone |

---

## 🛠️ Tech Stack

### Frontend
- **Next.js 14** (App Router)
- **Tailwind CSS** + **ShadCN UI**
- **Recharts** for data visualization
- **Supabase JS Client** for Realtime subscriptions

### Backend
- **FastAPI** (Python 3.11+)
- **SQLAlchemy** + **Alembic** for ORM and migrations
- **APScheduler** / **Celery + Redis** for background ML jobs
- **Pydantic v2** for schema validation

### Machine Learning
- **scikit-learn** — preprocessing, K-Means clustering
- **XGBoost** — gradient boosted demand forecasting
- **TensorFlow / Keras** — LSTM time-series model
- **pandas / NumPy** — feature engineering

### AI & Vector Search
- **OpenAI GPT-4o** — chatbot response generation
- **Pinecone** — vendor-scoped vector database
- **LangChain** — RAG orchestration

### Database & Auth
- **PostgreSQL** via **Supabase** (row-level security enabled)
- **Supabase Auth** + **JWT**

### Infrastructure
- **Vercel** — frontend hosting
- **Railway / Render** — backend + ML worker hosting
- **Supabase** — database + auth + storage
- **Redis** — task queue broker
- **Sentry** — error tracking

---

## 📁 Project Structure

```
food-demand-platform/
├── backend/                        # FastAPI application
│   ├── app/
│   │   ├── api/                    # Route handlers
│   │   │   ├── auth.py
│   │   │   ├── orders.py
│   │   │   ├── forecasts.py
│   │   │   ├── analytics.py
│   │   │   └── chat.py
│   │   ├── core/                   # Config, security, dependencies
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── dependencies.py
│   │   ├── db/                     # Database models & session
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   └── session.py
│   │   ├── ml/                     # ML pipeline
│   │   │   ├── preprocessing.py
│   │   │   ├── features.py
│   │   │   ├── clustering.py
│   │   │   ├── xgboost_model.py
│   │   │   ├── lstm_model.py
│   │   │   ├── evaluator.py
│   │   │   ├── forecaster.py
│   │   │   └── scheduler.py
│   │   ├── rag/                    # RAG chatbot
│   │   │   ├── embedder.py
│   │   │   ├── vector_store.py
│   │   │   └── chatbot.py
│   │   ├── integrations/           # External APIs
│   │   │   ├── weather.py
│   │   │   └── holidays.py
│   │   └── main.py                 # FastAPI app entry point
│   ├── alembic/                    # DB migrations
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                       # Next.js application
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── login/page.tsx
│   │   │   └── register/page.tsx
│   │   ├── dashboard/
│   │   │   ├── page.tsx            # Analytics overview
│   │   │   ├── orders/page.tsx
│   │   │   ├── forecasts/page.tsx
│   │   │   ├── inventory/page.tsx
│   │   │   └── chat/page.tsx
│   │   └── layout.tsx
│   ├── components/
│   │   ├── charts/
│   │   ├── orders/
│   │   ├── chatbot/
│   │   └── ui/                     # ShadCN components
│   ├── lib/
│   │   ├── api.ts                  # Axios API client
│   │   ├── supabase.ts
│   │   └── utils.ts
│   ├── types/
│   ├── public/
│   ├── tailwind.config.ts
│   ├── next.config.ts
│   └── package.json
│
├── docker-compose.yml              # Local dev orchestration
├── .env.example
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

| Tool | Version |
|---|---|
| Python | 3.11+ |
| Node.js | 18+ |
| PostgreSQL | 14+ (or Supabase project) |
| Redis | 7+ (for Celery task queue) |
| Docker | Optional, for local dev |

---

### Backend Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-org/food-demand-platform.git
cd food-demand-platform/backend

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and configure environment variables
cp ../.env.example .env
# Edit .env with your credentials (see Environment Variables section)

# 5. Run database migrations
alembic upgrade head

# 6. Start the FastAPI server
uvicorn app.main:app --reload --port 8000

# 7. (Optional) Start Celery worker for ML background jobs
celery -A app.ml.scheduler worker --loglevel=info
```

API docs available at: `http://localhost:8000/docs`

---

### Frontend Setup

```bash
cd food-demand-platform/frontend

# 1. Install dependencies
npm install

# 2. Copy environment variables
cp ../.env.example .env.local
# Fill in NEXT_PUBLIC_* variables

# 3. Start development server
npm run dev
```

Frontend available at: `http://localhost:3000`

---

### Using Docker Compose (Recommended for local dev)

```bash
# From the project root
docker-compose up --build
```

This starts:
- FastAPI backend on port `8000`
- Next.js frontend on port `3000`
- PostgreSQL on port `5432`
- Redis on port `6379`

---

### Environment Variables

Create a `.env` file in the project root using `.env.example` as a template:

```env
# ─── Database ───────────────────────────────────────────────
DATABASE_URL=postgresql://user:password@localhost:5432/food_platform
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# ─── Auth ────────────────────────────────────────────────────
JWT_SECRET_KEY=your-very-long-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# ─── OpenAI ──────────────────────────────────────────────────
OPENAI_API_KEY=sk-...

# ─── Pinecone ────────────────────────────────────────────────
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=us-east-1-aws
PINECONE_INDEX_NAME=food-platform-vectors

# ─── Weather ─────────────────────────────────────────────────
OPENWEATHER_API_KEY=your-openweathermap-key

# ─── Redis (Celery) ──────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ─── Frontend (Next.js) ──────────────────────────────────────
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

---

## 🤖 ML Pipeline

The ML pipeline runs automatically as a background job but can also be triggered manually.

### Pipeline Steps

```
Raw Order Data
     │
     ▼
1. Preprocessing      → Handle missing values, outliers, normalization
     │
     ▼
2. Feature Engineering → Day/Hour/Week, rolling averages, weather, festivals
     │
     ▼
3. K-Means Clustering  → Segment items by demand pattern
     │
     ▼
4a. XGBoost Training   → Tabular forecasting model
4b. LSTM Training      → Sequential time-series model
     │
     ▼
5. Evaluation          → RMSE, MAE, MAPE per vendor per model
     │
     ▼
6. Forecast Generation → Next 3 days: demand, revenue, inventory
     │
     ▼
7. Store & Serve       → Save to DB + expose via Prediction API
```

### Manual Trigger

```bash
# Trigger retraining for a specific vendor
curl -X POST http://localhost:8000/ml/retrain/{vendor_id} \
  -H "Authorization: Bearer <token>"
```

### Scheduler (Automatic)

The pipeline runs **daily at 2:00 AM UTC** via APScheduler or Celery Beat, processing all active vendors.

---

## 📡 API Reference

Full interactive docs: `http://localhost:8000/docs`

### Authentication
```
POST /auth/login          → Returns access token
POST /auth/register       → Register new vendor
POST /auth/refresh        → Refresh access token
```

### Orders
```
GET  /menu/{vendor_id}              → List menu items
POST /menu                          → Create menu item
POST /orders                        → Place order
GET  /orders/{vendor_id}            → List orders
PATCH /orders/{order_id}/status     → Update order status
```

### Forecasts & Analytics
```
GET /forecasts/{vendor_id}                  → 3-day demand forecasts
GET /analytics/{vendor_id}/revenue          → Revenue trend data
GET /analytics/{vendor_id}/top-items        → Top-selling items
GET /analytics/{vendor_id}/inventory        → Inventory insights
```

### Chatbot
```
POST /chat                          → Send message, get RAG response
GET  /chat/history/{vendor_id}      → Retrieve chat history
```

---

## ☁️ Deployment

### Frontend → Vercel
```bash
cd frontend
vercel --prod
```
Set all `NEXT_PUBLIC_*` environment variables in Vercel dashboard.

### Backend → Railway
1. Connect GitHub repo to Railway
2. Set root directory to `backend/`
3. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add all backend env variables in Railway dashboard

### Database → Supabase
1. Create a new Supabase project
2. Enable Row Level Security on all tables
3. Run migrations: `alembic upgrade head` (pointed at Supabase connection string)

### ML Worker → Railway (separate service)
```
Start command: celery -A app.ml.scheduler worker --loglevel=info
```

---

## 🧪 Running Tests

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=app

# Frontend tests
cd frontend
npm run test
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "feat: add your feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

Please follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
