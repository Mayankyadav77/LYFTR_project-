# Lyftr AI — Full-Stack AI Chatbot with Key Failover & Response Caching

A production-ready full-stack AI chatbot built with **React + Vite**, **FastAPI**, **LiteLLM**, and **SQLite**.

---

## 1. Live URLs
- **Frontend Live URL**: `https://<your-project>.vercel.app`
- **Backend Live URL**: `https://<your-service>.onrender.com`
- **GitHub Repository**: `https://github.com/<username>/<repo-name>`

---

## 2. Run Locally

### Prerequisites
- Python 3.11+
- Node.js 20+ & npm
- Docker & Docker Compose (optional for containerized setup)

### With Docker & Makefile
1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Start the services:
   ```bash
   make up
   ```
   Or without Make:
   ```bash
   docker compose up -d --build
   ```
- Frontend UI: [http://localhost:3000](http://localhost:3000)
- Backend API: [http://localhost:8000](http://localhost:8000) (Docs: [http://localhost:8000/docs](http://localhost:8000/docs))

### Without Docker

#### Backend Setup
```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Run test suite:
```bash
pytest tests -v
```

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev -- --port 3000
```
Open [http://localhost:3000](http://localhost:3000).

---

## 3. Deployment Instructions

### A. Deploy Backend to Render (FastAPI + Docker)

1. **Push your repository to GitHub** (ensure `.env` is never committed; `.gitignore` is already set).
2. Go to [Render Dashboard](https://dashboard.render.com/) and click **New +** -> **Web Service**.
3. Select your repository.
4. Configure the Web Service:
   - **Name**: `lyftr-ai-backend` (or your choice)
   - **Region**: Choose the closest region
   - **Branch**: `master` (or `main`)
   - **Root Directory**: `backend`
   - **Runtime**: **Docker**
5. **Attach Persistent Disk (Mandatory for SQLite)**:
   - Scroll to **Disks** section and click **Add Disk**.
   - **Name**: `sqlite_data`
   - **Mount Path**: `/data`
   - **Size**: 1 GB (sufficient for SQLite)
6. **Set Environment Variables**:
   In the **Environment Variables** tab, add:
   | Key | Value | Description |
   | :--- | :--- | :--- |
   | `LLM_API_KEYS` | `AIzaSy...,AIzaSy...` | Comma-separated list of at least 2 real Gemini API keys |
   | `LLM_MODEL` | `gemini/gemini-2.5-flash` | Gemini model name |
   | `DATABASE_URL` | `sqlite:////data/app.db` | Points to SQLite inside the persistent disk |
   | `ALLOWED_ORIGINS` | `*` or `https://<your-app>.vercel.app` | Frontend origin(s) permitted for CORS |
   | `ENABLE_FAILURE_SIMULATION` | `true` | Required for failover demonstration |
7. Click **Deploy Web Service**.
8. Once live, test: `https://<your-render-service>.onrender.com/health`. It should return:
   ```json
   {"status": "ok", "keys_configured": 2, "cache_enabled": true}
   ```

---

### B. Deploy Frontend to Vercel (React + Vite)

1. Go to [Vercel Dashboard](https://vercel.com/) and click **Add New...** -> **Project**.
2. Import the same GitHub repository.
3. In **Configure Project**:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click edit and select `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. **Set Environment Variables**:
   Add this environment variable:
   | Key | Value |
   | :--- | :--- |
   | `VITE_API_URL` | `https://<your-render-service>.onrender.com` |
   *(Note: Do not include a trailing slash; the app automatically normalizes it).*
5. Click **Deploy**.
6. When deployment finishes, update the backend's `ALLOWED_ORIGINS` variable on Render to match your Vercel domain if you prefer strict origin matching (e.g. `https://lyftr-ai.vercel.app`).

---

## 4. Design Decisions
- **Key Fallback Mechanism**: The backend parses `LLM_API_KEYS` sequentially (`key_1`, `key_2`, ...). On rate limits (HTTP 429), quota limits, or 5xx errors, it transparently retries on the next key without breaking the UI. When all keys fail, it returns HTTP 503 `{"detail": "all providers unavailable"}` without adding the failed query to SQLite history.
- **Exact Caching**: LiteLLM local caching indexes a SHA-256 hash of `model` + the full message list (system prompt + history + new message). Cache hits return `LLM_CACHE`, `key_id: null`, and stored tokens.
- **SQLite Storage**: Conversation turns are persisted in SQLite (`messages` table) mounted on `/data`, surviving server restarts and deployments.

---

## 5. Verification
- **Automated Tests**: Run `pytest backend/tests -v`.
- **Cache Hit Demonstration**: Send identical messages in two sessions; the second will return `LLM_CACHE` with zero fallback attempts.
- **Failover Demonstration**: Send message with `X-Simulate-Failure: key_1=429` to observe fallback to `key_2`. Send `*=429` to observe clean HTTP 503 error handling.

---

## 6. Setup Used
- IDE: Antigravity IDE / VS Code
- AI Model: Gemini 2.5 Flash via LiteLLM Gateway
- Frameworks: FastAPI (Python 3.11), React 18 + Vite (Node 20)
