# Codebase Stack

**Date:** 2026-05-12

## Core Technologies

### Backend
- **Framework:** FastAPI (0.111.0)
- **Language:** Python 3.10
- **Process Manager:** Gunicorn with Uvicorn workers (`gunicorn==22.0.0`, `uvicorn[standard]==0.30.1`)
- **Database ORM:** SQLAlchemy Asyncio (`sqlalchemy[asyncio]==2.0.30`)
- **Migrations:** Alembic (`alembic==1.13.1`)
- **Driver:** Asyncpg (`asyncpg==0.29.0`)

### Frontend
- **Framework:** Next.js (16.2.6) with React 19
- **Language:** TypeScript
- **Styling:** TailwindCSS v4 with `class-variance-authority` and `clsx`
- **UI Components:** Radix UI primitives (`@radix-ui/react-*`), Lucide React icons
- **Forms & Validation:** React Hook Form (`react-hook-form`), Zod (`zod`)
- **Data Visualization:** Recharts (`recharts`)

### Data & ML Pipeline
- **Caching & Rate Limiting:** Redis Async (`redis==5.0.7`)
- **Machine Learning:** Scikit-learn, XGBoost, Pandas, NumPy
- **Background Jobs:** Celery (planned/configured), APScheduler

### Security
- **Auth:** JWT (`python-jose[cryptography]`)
- **Password Hashing:** Bcrypt (`passlib[bcrypt]`)
- **Frontend Protection:** Strict Content-Security-Policy (CSP) via Vercel Edge headers.

## Configuration & Deployment
- **Backend Env:** Pydantic Settings (`pydantic-settings`)
- **Frontend Hosting:** Vercel (configured via `vercel.json`)
- **Backend Containerization:** Docker (Multi-stage build, non-root user, slim python base)
