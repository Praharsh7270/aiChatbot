# AI Chatbot (FastAPI + React + Vite)

This repository contains a small AI Chatbot application with a FastAPI backend and a React + Vite frontend.

Overview
--------
- Backend: FastAPI app that wraps a LangGraph/ LangChain flow and an LLM (configured to use OpenRouter / DeepSeek). It exposes a single `/chat` endpoint that accepts a user message and an optional `thread_id` and returns the assistant response.
- Frontend: React app (Vite) providing a chat UI that sends messages to the backend and displays responses.

This README explains what each part does, how to run the project locally (Windows), what to change, and common troubleshooting tips.

Repository layout (important files)
---------------------------------
- backend/
  - `api.py` - FastAPI application and the `/chat` endpoint. Reads API key via python-dotenv.
  - `chatbot.py` - a local runnable example of the LangGraph chatbot.
  - `requirements.txt` - Python dependencies (includes `python-dotenv`, `fastapi`, `uvicorn`, etc.).
  - `.env.example` - copy to `.env` and add your API key.
  - `.gitignore` - local ignore rules (note: this repo currently ignores its own `.gitignore` files per workspace settings).
- frontend/
  - `index.html`, `src/` - React + Vite sources. Main chat UI is `src/components/Chat.jsx`.
  - `vite.config.js` - development server config. It contains a dev proxy for `/chat` -> `http://localhost:8000`.
  - `package.json` - frontend dependencies & scripts.

How it works (end-to-end)
-------------------------
1. User types a message in the React UI and presses Enter / Send.
2. The frontend (Chat.jsx) POSTs to `/chat` with JSON: `{ user_message, thread_id }`.
3. FastAPI's `/chat` endpoint wraps the user message in a `HumanMessage`, invokes the compiled LangGraph state machine with `chatbot.ainvoke(...)` and passes the `thread_id` as part of config.
4. The LLM (configured in `api.py` / `chatbot.py`) returns an AI message. The endpoint responds with `{ response_content, thread_id }`.
5. The frontend reads `response_content` and appends it to the chat UI.

Environment and secrets
-----------------------
- The backend uses `python-dotenv` and will load `.env` in `backend/` (see `backend/.env.example`).
- Required env variable (one of):
  - `OPENROUTER_API_KEY` (preferred for OpenRouter)
  - `OPENAI_API_KEY` (fallback)
- Example: create `backend/.env` from `backend/.env.example` and set your key.

Local development (Windows - cmd.exe)
-----------------------------------
Prerequisites:
- Python 3.8+ (recommended 3.10+)
- Node.js (LTS)

Backend
1. Open a terminal and install Python deps:

```cmd
cd c:\Users\hp\Desktop\ml\project1\backend
pip install -r requirements.txt
```

2. Create `.env` and add your API key:

```cmd
copy .env.example .env
rem # then edit .env in an editor and set OPENROUTER_API_KEY=sk-or-...
```

3. Run the backend:

```cmd
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

Frontend
1. In another terminal, install frontend deps and start the dev server:

```cmd
cd c:\Users\hp\Desktop\ml\project1\frontend
npm install
npm run dev
```

2. Open the site (usually `http://localhost:5173`) and use the chat UI.

Notes about the dev proxy and CORS
- The Vite dev server includes a proxy for `/chat` to `http://localhost:8000` (see `vite.config.js`) so requests from the browser go through the dev server and avoid CORS issues.
- The backend also has `CORSMiddleware` configured for the dev origin.

Production / build notes
- When building the frontend for production with `npm run build`, Vite will bake in any environment variable prefixed with `VITE_` at build time. To target a production backend, set `VITE_API_URL` before building or in your deployment configuration.
- Example (build-time env):

```cmd
set VITE_API_URL=https://your.api.host
npm run build
```

What to edit (common tweaks)
----------------------------
- Change the LLM model or settings: edit `backend/api.py` (or `backend/chatbot.py` for the standalone runnable). Look for `ChatOpenAI(...)` and change `model`, `openai_api_base`, `timeout`, `max_retries`, etc.
- Change the frontend API base: set `VITE_API_URL` in the environment (or update `const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000'` in `Chat.jsx`).
- Persist chat history: the example uses a local `SqliteSaver` in `chatbot.py`; change the DB path or storage strategy as needed.

QA — Quick questions & answers
--------------------------------
Q: Why did I see "Failed to fetch" in the browser but the backend works in Postman?
A: Browsers enforce CORS and send a preflight OPTIONS request. Postman does not. The project adds both a Vite proxy and `CORSMiddleware` in the backend to avoid this; ensure the backend is running and that `CORSMiddleware` allows your frontend origin.

Q: What is `thread_id`?
A: `thread_id` tracks a conversation session. Pass the same `thread_id` to continue the same thread/session. The backend expects a string (not null); the frontend sends an empty string if none exists.

Q: Where is the LLM API key stored?
A: In `backend/.env` (use `OPENROUTER_API_KEY` or `OPENAI_API_KEY`). Do NOT commit this file. The repo includes `.env.example` to show the variable name.

Q: Can I run this on a device (my laptop, Raspberry Pi, or cloud VM)?
A: Yes. Steps are the same: ensure Python and Node are installed on the device, set the env variables, install dependencies, and run backend + frontend. For production deployment use a process manager (systemd, pm2) or containerize with Docker.

Troubleshooting
---------------
- If the frontend shows `Error: Failed to fetch`:
  - Confirm backend is running and listening on port 8000.
  - Check the browser network tab for the `/chat` request and the server logs for any exceptions.
  - Ensure `.env` contains a valid API key.
- If you get an LLM error (500), inspect the backend logs for the exception (timeout, rate limits, key invalid, etc.).

Security & git
--------------
- Do not commit `backend/.env` or any file containing API keys. `.gitignore` is configured to ignore `.env` files.
- Note: the repository currently has the `.gitignore` files themselves ignored (per workspace). This means changes to the ignore lists won't be tracked. If you want the ignore rules tracked, remove the `.gitignore` entry from the ignore files and commit them.

Further improvements (suggested)
------------------------------
- Add tests for the backend endpoint and a small integration test for the frontend (e.g., play a request against a mock server).
- Add a production deployment section (Dockerfile, docker-compose, or cloud deploy script).
- Add request/response logging, rate limit handling, and error reporting for the LLM calls.

Contact / Next steps
--------------------
If you want, I can:
- Run the servers here and verify the UI end-to-end and share the logs.
- Create a simple Dockerfile and `docker-compose.yml` to run both services easily.
- Add a top-level `.gitignore` and move common entries there instead of ignoring `.gitignore` itself.

---
README generated from repo analysis on 2025-11-15.
