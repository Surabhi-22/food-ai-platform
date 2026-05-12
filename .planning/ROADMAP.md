# Project Roadmap

This document outlines the sequential phases to deliver the Food AI Demand Platform.

---

## 🏆 MILESTONE v1.0 (COMPLETED)

### Phase 1: ML Pipeline Foundation (Completed)
- **Goal:** Build the XGBoost/LSTM infrastructure to make demand predictions.

### Phase 2: Analytics Dashboard (Next.js) (Completed)
- **Goal:** Visualize backend analytics via a Next.js UI.

### Phase 3: RAG Chatbot Integration (Completed)
- **Goal:** Implement the AI Vendor Chatbot.

### Phase 4: External Integrations & Tuning (Completed)
- **Goal:** Augment ML accuracy with weather/festivals and finalize performance tuning.

---

## 🏗️ MILESTONE v1.1 (ACTIVE)

### Phase 5: Backend Testing & CI Pipeline
- **Goal:** Solidify backend reliability with Pytest and continuous integration.
- **Scope:** 
  - Write unit tests for FastAPI CRUD, routes, and ML background workers.
  - Fix MyPy typing warnings across the backend.
  - Create `.github/workflows/backend-test.yml` for automated CI.
- **Requirements:** TEST-01, TEST-03
- **Dependencies:** None (v1.0 completed).

### Phase 6: Frontend Testing & Linting
- **Goal:** Ensure UI stability with Jest and React Testing Library.
- **Scope:** 
  - Write unit tests for Recharts components, Chat UI, and Analytics Page.
  - Fix ESLint and SonarQube warnings.
  - Create `.github/workflows/frontend-test.yml` for automated CI.
- **Requirements:** TEST-02, TEST-04
- **Dependencies:** Phase 5.
