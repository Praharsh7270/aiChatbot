# --- 0. IMPORTS ---
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv, dotenv_values

# Load environment variables from a .env file if present (development)
load_dotenv()
env_values = dotenv_values()


# --- 1. LLM SETUP ---
api_key = env_values.get("OPENROUTER_API_KEY") or env_values.get("OPENAI_API_KEY")
if not api_key:
    # fallback to environment variables if not present in .env
    import os
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError(
        "No API key found. Set the OPENROUTER_API_KEY or OPENAI_API_KEY environment variable or add it to a .env file."
    )

llm = ChatOpenAI(
    model="deepseek/deepseek-r1-0528-qwen3-8b:free",
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=api_key,
    timeout=20,                 # <--- important
    max_retries=2               # <--- important
)


# --- 2. LANGGRAPH STATE ---
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# --- 3. NODE LOGIC ---
async def chat_node(state: ChatState):
    try:
        response = await llm.ainvoke(state["messages"])
        return {"messages": [response]}
    except Exception as e:
        return {"messages": [HumanMessage(content=f"LLM error: {str(e)}")]}


# --- 4. BUILD THE GRAPH ---
graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)

chatbot = graph.compile()


# --- 5. FASTAPI ---
app = FastAPI(title="LangGraph Chatbot API")

# Allow browser requests from the frontend dev server (and others during development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request model
class ChatInput(BaseModel):
    user_message: str
    thread_id: str


# Response model
class ChatResponse(BaseModel):
    response_content: str
    thread_id: str


# --- 6. ENDPOINT ---
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(input_data: ChatInput):

    human_message = HumanMessage(content=input_data.user_message)

    config = {
        "configurable": {
            "thread_id": input_data.thread_id
        }
    }

    try:
        response_state = await chatbot.ainvoke(
            {"messages": [human_message]},
            config=config
        )

        final_response = response_state["messages"][-1].content

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ChatResponse(
        response_content=final_response,
        thread_id=input_data.thread_id
    )


# --- 7. RUN SERVER ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
