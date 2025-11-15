# Chatbot Frontend (React + Vite)

This is a minimal React + Vite frontend that connects to your FastAPI backend at `/chat`.

Features:
- Simple chat UI with user and bot messages
- Persists `thread_id` in localStorage so the conversation continues
- Configurable backend URL via `VITE_API_URL` environment variable

Getting started

1. Copy `.env.example` to `.env` and edit if necessary:

   VITE_API_URL=http://localhost:8000

2. Install dependencies and run dev server:

```bash
# Windows (cmd.exe)
npm install
npm run dev
```

3. Open the dev server (Vite default) in your browser: http://localhost:5173

Notes

- The frontend expects your FastAPI backend to expose POST `/chat` accepting JSON { user_message, thread_id? } and returning { response, thread_id }.
- The backend `api.py` in your project already configures CORS for `http://localhost:5173`. If you run the frontend on a different port, update CORS and `VITE_API_URL`.

Enhancements you might want next

- Add message streaming for partial AI responses
- Add typing indicator and message timestamps
- Add authentication if your backend requires it

