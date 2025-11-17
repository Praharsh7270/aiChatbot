% # AI Chatbot (FastAPI backend + React + Vite frontend)

This repository contains a small AI Chatbot application with a FastAPI backend and a React + Vite frontend. The backend uses a LangGraph/LangChain flow and an LLM; the frontend provides a friendly chat UI.

## Highlights

- FastAPI backend with a `/chat` endpoint that drives a LangGraph agent (chat + tool routing).
- React + Vite frontend with an improved chat UI:
  - Animated bot text generation (typewriter-style) for better UX.
  - Tool badges: when the assistant calls an external tool (Wikipedia, DuckDuckGo, etc.), the UI displays a small badge showing which tool was used.

## Repository layout

- `backend/`
  - `api.py` - FastAPI app and `/chat` endpoint (production entry point).
  - `chatbot.py` - standalone runnable example of the LangGraph chatbot (used for local CLI testing).
  - `requirements.txt` - Python dependencies for the backend.
  - `.env.example` - example environment file; copy to `.env` and add your API key.
- `frontend/`
  - `src/components/Chat.jsx` - main chat UI (typewriter effect + tool badges).
  - `src/styles.css` - UI styles for the chat.
  - `package.json`, `vite.config.js` - frontend scripts and dev proxy config.

## How it works (end-to-end)

1. User types a message in the React UI and presses Enter / Send.
2. The frontend POSTs to `/chat` with JSON: `{ user_message, thread_id }`.
3. FastAPI's `/chat` endpoint wraps the message in a `HumanMessage` and invokes the LangGraph graph. The graph may return an AI response directly or include tool calls.
4. If the agent calls a tool, the backend executes the tool and returns the tool output. The backend includes tool metadata in the response so the frontend can display a tool badge.
5. The frontend displays the assistant response. Bot responses are animated; if a tool was called, a badge like `wikipedia_tool` appears above the response.

## Environment and secrets

- The backend uses `python-dotenv` and will load `backend/.env` (copy `backend/.env.example` to `.env`).
- Required environment variable (one of):
  - `OPENROUTER_API_KEY` (for OpenRouter)
  - `OPENAI_API_KEY` (fallback)

## Local development (Windows - cmd.exe)

Prerequisites:
- Python 3.10+ (recommended)
- Node.js (LTS)

### Backend (install and run)
1. Install Python dependencies:

```cmd
cd c:\Users\hp\Desktop\ml\project1\backend
pip install -r requirements.txt
```

2. Create `.env` and add your API key:

```cmd
copy .env.example .env
rem # then open backend\.env in an editor and set OPENROUTER_API_KEY or OPENAI_API_KEY
```

3. Run the backend (development):

```cmd
cd c:\Users\hp\Desktop\ml\project1\backend
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (install and run)
1. Install dependencies and start the dev server:

```cmd
cd c:\Users\hp\Desktop\ml\project1\frontend
npm install
npm run dev
```

2. Open the site (usually `http://localhost:5173`) and use the chat UI.

## Notes about the dev proxy and CORS

- Vite dev server includes a proxy for `/chat` to `http://localhost:8000` (see `vite.config.js`) so browser requests avoid CORS issues.
- The backend also configures `CORSMiddleware` for the dev origin.

## Frontend UX details

- Animated generation: bot responses are shown with a typewriter-style reveal. This improves readability and gives a sense of streaming.
- Tool badges: when the assistant calls a tool, the backend prefixes or annotates the response so the frontend can show a badge, e.g. `(tool: wikipedia_tool) ...` or structured responses. The UI then displays the badge above the response.

If you prefer structured tool metadata instead of a prefix, I can update the API to return JSON like `{ response: string, tool: 'wikipedia_tool' }` and wire the frontend to read that directly.

## Production / build notes

- When building the frontend for production, set `VITE_API_URL` to your backend URL at build time. Example:

```cmd
set VITE_API_URL=https://your.api.host
npm run build
```

## Other tweaks

- Change the LLM model or settings by editing `backend/api.py` (or `backend/chatbot.py` for standalone tests). Look for `ChatOpenAI(...)`.
- Change frontend API base: set `VITE_API_URL` or edit `Chat.jsx`'s `apiBase` default.

## Troubleshooting

- If the frontend shows `Error: Failed to fetch`:
  - Confirm the backend is running on port 8000 and accessible.
  - Check browser devtools network tab for the `/chat` request and backend logs for exceptions.
  - Ensure `backend/.env` contains a valid API key.
- If you see pydantic validation errors from tools, ensure the backend normalizes tool inputs before calling library methods — that has been addressed in recent updates.

## Requirements & installation notes

- Backend requirements are listed in `backend/requirements.txt`. Install them with:

```cmd
pip install -r backend\requirements.txt
```

- Some packages (langgraph, langchain-core, langchain-community) may require compatible versions; if you run into installation issues, share the pip output and I'll suggest pinned versions.

## Security & git

- Do not commit your `backend/.env` or any file containing API keys. The repo provides `.env.example` for reference.

## Next steps I can help with

- Convert the backend->frontend contract to structured JSON for tool metadata and update the frontend to rely on that (recommended).
- Add a Dockerfile and `docker-compose.yml` for easy local deployment.
- Add tests and CI for the API and the frontend component.

If you want any of these, tell me which and I'll implement it.

---
README updated to reflect UI improvements and dependency changes (2025-11-17).
