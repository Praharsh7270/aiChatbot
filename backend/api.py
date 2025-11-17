# --- 0. IMPORTS ---
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun, WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
import os
from dotenv import load_dotenv, dotenv_values
# SqliteSaver may not exist in all langgraph releases/installs. Import defensively.
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except Exception:
    SqliteSaver = None
import sqlite3
import uvicorn
import requests
import traceback

# -------------------------------------------------------
# SETUP & LLM CONFIGURATION
# -------------------------------------------------------

load_dotenv()
env_values = dotenv_values()

# Ensure API Key is available
api_key = env_values.get("OPENROUTER_API_KEY") or env_values.get("OPENAI_API_KEY")
if not api_key:
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("No API key found.")

os.environ["LANGCHAIN_TRACING_V2"] = "true"

# --- 1. TOOLS DEFINITION ---

# 🔍 DuckDuckGo Search Tool
ddg_search = DuckDuckGoSearchRun()

# 📚 Wikipedia Tool
wiki_tool = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())

# 🧮 Calculator Tool
@tool
def calculator_tool(first_num: float, second_num: float, operation: str) -> dict:
    """Perform a basic arithmetic operation on two numbers. Supported operations: add, sub, mul, div"""
    try:
        op_map = {"add": "+", "sub": "-", "mul": "*", "div": "/"}
        if operation not in op_map:
            return {"error": f"Unsupported operation '{operation}'"}
        if operation == "div" and second_num == 0:
            return {"error": "Division by zero is not allowed"}
        
        # Using eval here for simple calculation is acceptable for internal tools
        result = eval(f"{first_num} {op_map[operation]} {second_num}")
        return {"first_num": first_num, "second_num": second_num, "operation": operation, "result": result}
    except Exception as e:
        return {"error": str(e)}

# 📈 Stock Price Tool
@tool
def stock_tool(symbol: str):
    """Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA') using Alpha Vantage."""
    # NOTE: Using a public/placeholder key. This tool is highly prone to rate-limiting errors.
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=3DDZ72FTDBKOTKX9"
    try:
        r = requests.get(url)
        r.raise_for_status() 
        data = r.json()
        
        if "Error Message" in data:
            return f"Alpha Vantage Error: {data['Error Message']}"
        if "Note" in data and "limit" in data["Note"].lower():
            return f"Alpha Vantage Rate Limit Exceeded: {data['Note']}"
        
        if "Global Quote" in data and data["Global Quote"]:
            quote = data["Global Quote"]
            if '05. price' in quote:
                return {"symbol": symbol, "price": quote['05. price']}
            
        return f"Could not find stock quote for {symbol}. API response: {data}"
    
    except Exception as e:
        return f"Stock Tool Runtime Error: {str(e)}"


# --- LLM with Tool Binding ---
llm = ChatOpenAI(
    model="google/gemini-2.0-flash-001",
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=api_key,
    timeout=20,
    max_retries=2
).bind_tools([
    ddg_search,
    wiki_tool,
    calculator_tool, 
    stock_tool,
])


# --- 2. STATE ---
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# --- 3. CHAT NODE (The Router) ---
async def chat_node(state: ChatState):
    """Invokes the LLM to decide on the next action (respond or call tool)."""
    try:
        # Use ainvoke for async compatibility with FastAPI
        response = await llm.ainvoke(state["messages"])
        return {"messages": [response]}
    except Exception as e:
        print(f"LLM ERROR: {e}")
        return {"messages": [AIMessage(content=f"Error communicating with LLM: {str(e)}")]}


# --- 4. TOOL NODE (The Executor) ---
def tool_node(state: ChatState):
    """Executes any tool calls requested by the LLM."""
    last_msg = state["messages"][-1]
    
    if not hasattr(last_msg, "tool_calls") or not last_msg.tool_calls:
        # Should not happen in a correctly routed graph, but good for safety
        return {"messages": [AIMessage(content="No tool call detected")]}

    outputs = []
    
    # Map tool names (as used by the LLM) to the actual tool objects
    tool_map = {
        "duckduckgo_search": ddg_search,
        "wikipedia": wiki_tool,
        "calculator_tool": calculator_tool, 
        "stock_tool": stock_tool,           
    }
    
    for call in last_msg.tool_calls:
        name = call["name"]
        args = call["args"]
        tool_call_id = call["id"]
        
        print(f"[TOOL] Calling {name} with arguments: {args}")

        try:
            tool_to_call = tool_map.get(name)

            if not tool_to_call:
                out = f"Unknown tool: {name}. Available tools: {list(tool_map.keys())}"
            
            # Handling for single-input runnables (DuckDuckGo, Wikipedia)
            elif name in ["duckduckgo_search", "wikipedia"]:
                query = args.get('query') or args.get('input') or list(args.values())[0]
                out = tool_to_call.invoke(query)
            
            # Handling for custom @tool functions (Calculator, Stock)
            elif name in ["calculator_tool", "stock_tool"]:
                out = tool_to_call.invoke(args) 
            
            else:
                 out = f"Tool '{name}' not mapped correctly."

        except Exception as e:
            tb = traceback.format_exc()
            print(f"[TOOL ERROR] {name} raised {type(e).__name__}: {e}\n{tb}")
            out = f"Tool '{name}' failed: {type(e).__name__}: {e}"

        if not isinstance(out, str):
            out = str(out)

        # Package the result into a ToolMessage for the LLM
        outputs.append(
            ToolMessage(
                content=out,
                tool_call_id=tool_call_id,
                name=name
            )
        )

    return {"messages": outputs}


conn = sqlite3.connect(database="chatbot5.db", check_same_thread=False)
if SqliteSaver is not None:
    try:
        checkpointer = SqliteSaver(conn=conn)
    except Exception as e:
        print(f"Warning: SqliteSaver import succeeded but initialization failed: {e}")
        checkpointer = None
else:
    print("Warning: langgraph.checkpoint.sqlite.SqliteSaver not available. Continuing without persistent checkpointer.")
    checkpointer = None


# --- 5. GRAPH DEFINITION ---
graph = StateGraph(ChatState)
graph.add_node("chat", chat_node)
graph.add_node("tool", tool_node)

# Entry point
graph.add_edge(START, "chat")

# Conditional Edge: Decide whether to go to the tool or end
graph.add_conditional_edges(
    "chat",
    # Check if the last message has tool calls
    lambda state: "tool" if hasattr(state["messages"][-1], "tool_calls") and state["messages"][-1].tool_calls else END,
    {
        "tool": "tool",
        END: END
    }
)

# Tool execution always loops back to the chat node for synthesis
graph.add_edge("tool", "chat")

if checkpointer is not None:
    chatbot = graph.compile(checkpointer=checkpointer)
else:
    chatbot = graph.compile()


# -------------------------------------------------------
# FASTAPI APPLICATION
# -------------------------------------------------------

app = FastAPI(title="LangGraph Tool Agent API")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        # Add your vercel app domain here
        "https://ai-chatbot-ioo5-hcwa63db1-praharsh-singhs-projects.vercel.app/", 
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatInput(BaseModel):
    user_message: str
    thread_id: str

class ChatResponse(BaseModel):
    response_content: str
    thread_id: str


# --- 6. CHAT ENDPOINT ---
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(input_data: ChatInput):
    """Processes user message through the LangGraph agent."""
    
    human_message = HumanMessage(content=input_data.user_message)
    
    # Define config for memory persistence via thread_id
    config = {
        # IMPORTANT: LangGraph uses the thread_id for checkpointing (memory)
        "configurable": {"thread_id": input_data.thread_id}, 
        "run_name": "tool-agent-run",
        "metadata": {"user": "frontend"}
    }
    
    try:
        # Await the async invocation of the compiled graph
        response_state = await chatbot.ainvoke(
            {"messages": [human_message]},
            config=config
        )
        
        # Extract the final AIMessage content
        final_message = response_state["messages"][-1]
        final_response = final_message.content

    except Exception as e:
        print(f"API Invocation Error: {e}")
        # Return a 500 status code with the error detail
        raise HTTPException(status_code=500, detail=f"Agent runtime error: {str(e)}")

    return ChatResponse(
        response_content=final_response,
        thread_id=input_data.thread_id
    )

# --- Utility Endpoint ---
@app.get("/ping")
def ping():
    return {"message": "pong"}

# --- 7. RUN ---
if __name__ == "__main__":
    # Ensure uvicorn is installed (pip install uvicorn)
    uvicorn.run(app, host="0.0.0.0", port=8000)