# Lyftr AI — Full-Stack AI Chatbot with Key Failover & Response Caching

A production-ready full-stack AI chatbot built with **React + Vite**, **FastAPI**, **LiteLLM**, and **SQLite**.

---

## 1. Live URLs
- **Frontend Live URL**: `https://lyftr-ai-frontend.vercel.app` (or configured deployment URL)
- **Backend Live URL**: `https://lyftr-ai-backend.onrender.com` (or configured deployment URL)
- **GitHub Repository**: `https://github.com/<username>/lyftr-ai`

---

## 2. Run Locally

### Prerequisites
- Python 3.11+
- Node.js 20+ & npm
- Docker & Docker Compose (optional for containerized setup)

### With Docker & Makefile (Recommended)
1. Clone this repository and configure environment variables:
   ```bash
   cp .env.example .env
   # Add your Gemini API keys in .env
   ```
2. Start the entire stack with Docker Compose:
   ```bash
   make up
   ```
3. Stop the services:
   ```bash
   make down
   ```
- Frontend UI: [http://localhost:3000](http://localhost:3000)
- Backend API & Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### Without Docker

#### Backend Setup
```bash
cd backend
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
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
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 3. Design Decisions

### Key Fallback Mechanism
- Configured via comma-separated list of keys in `LLM_API_KEYS` (parsed in order into `key_1`, `key_2`, ...).
- On any HTTP 429, quota exhaustion, 5xx error, or simulated failure, the backend catches the error, increments `fallback_attempts`, and transparently routes to the next key in the pool.
- If all configured keys fail, the backend returns a clean HTTP 503 `{"detail": "all providers unavailable"}` without adding the failed prompt to the database session history.

### Response Caching
- Enabled via LiteLLM's local cache engine.
- Exact Cache Key Specification: `model` + the canonical full message list (system prompt + session history + new user message) hashed with SHA-256.
- Cache hits return resolution source `LLM_CACHE` with zero fallback attempts and `key_id: null`. The reply matches the cached response verbatim and displays significantly lower latency.
- Fresh generations return resolution source `LIVE_INFERENCE` alongside `key_id` and token counts.

### SQLite Multi-turn Session Storage
- Multi-turn conversation state is persisted per `session_id` in SQLite.
- Standardized data model storing `session_id`, `role`, `content`, `metadata` (JSON serialized), and `created_at` timestamp.
- Survives container restarts using Docker named volume mounted at `/data`.
- Client only transmits the new message; the backend automatically retrieves earlier context from SQLite for the LLM prompt.

---

## 4. Verification

### Automated Verification
Run the backend test suite covering health, validation errors (422), caching (LIVE_INFERENCE vs LLM_CACHE), key failover (X-Simulate-Failure), and session history (404 and 200):
```bash
pytest backend/tests -v
```

### Manual Verification via UI and API

#### 1. Live Inference & Metadata Display
- Send a message in the UI:
  - Verify that `meta-source` displays `LIVE_INFERENCE`.
  - Verify `meta-model`, `meta-latency`, `meta-input-tokens`, `meta-output-tokens`, and `key_id` are displayed.

#### 2. Caching Verification
- Open a new chat session (or click **New Chat**).
- Send the exact same initial query as before.
- Notice that `meta-source` transitions to `LLM_CACHE`, `key_id` is null, and latency drops significantly.

#### 3. Failover Verification (`X-Simulate-Failure`)
- In the sidebar under **X-Simulate-Failure Hook**, enter `key_1=429` and send a message.
  - Notice the response succeeds with `key_id: key_2` and `fallback_attempts: 1`.
- Enter `*=429` and send a message.
  - Notice the UI renders a clean 503 error banner: `Error (503): all providers unavailable` without breaking the screen.

#### 4. API Endpoints
- `GET /health` -> `{"status": "ok", "keys_configured": 2, "cache_enabled": true}`
- `POST /chat` -> `{ "session_id": "...", "reply": "...", "metadata": { ... } }`
- `GET /sessions/{session_id}/messages` -> `{ "session_id": "...", "messages": [ ... ] }`

---

## 5. Setup Used
- **IDE**: Visual Studio Code / Antigravity IDE
- **AI Assist**: Antigravity Full-Stack AI Engineer
- **Environment**: Windows 11 & Linux (Docker Alpine / Slim)

---

## 6. Bonus Features
- **Simulation Hook Presets**: UI quick-action buttons to inject `key_1=429`, `key_1=500`, and `*=429` directly from the sidebar.
- **Custom System Prompt**: Real-time adjustable system prompt per session via `data-testid="system-prompt-input"`.
- **Live Health Status Card**: Sidebar badge providing real-time backend connectivity, key count, and cache status.
- **Responsive Dark Theme UI**: Polished ChatGPT-style interface with smooth scrolling, error handling banners, and glowing badge indicators.
