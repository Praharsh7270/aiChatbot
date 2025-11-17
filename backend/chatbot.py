from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI

from langchain_community.tools import DuckDuckGoSearchRun, WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_core.tools import tool
import os
from dotenv import load_dotenv
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except Exception:
    SqliteSaver = None
import sqlite3
import requests
import traceback

# -------------------------------------------------------
# LOAD ENV
# -------------------------------------------------------
load_dotenv()

# -------------------------------------------------------
# TOOLS
# -------------------------------------------------------

# 🔍 DuckDuckGo Search Tool
ddg_search = DuckDuckGoSearchRun()

# 📚 Wikipedia Tool
wiki_tool = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())

# 🧮 Calculator Tool
@tool
def calculator_tool(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div
    """
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation '{operation}'"}
        
        return {"first_num": first_num, "second_num": second_num, "operation": operation, "result": result}
    except Exception as e:
        return {"error": str(e)}

# 📈 Stock Price Tool
@tool
def stock_tool(symbol: str):
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA') 
    using Alpha Vantage with API key in the URL.
    """
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=3DDZ72FTDBKOTKX9"
    
    try:
        r = requests.get(url)
        r.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        data = r.json()
        
        # Check for Alpha Vantage specific error messages
        if "Error Message" in data:
            return f"Alpha Vantage Error: {data['Error Message']}"
        if "Note" in data and "limit" in data["Note"].lower():
            return f"Alpha Vantage Rate Limit Exceeded: {data['Note']}"
        
        # Check if the Global Quote data exists
        if "Global Quote" in data and data["Global Quote"]:
            quote = data["Global Quote"]
            if '05. price' in quote:
                price = quote['05. price']
                return {"symbol": symbol, "price": price}
            else:
                 return f"Quote found but price is missing or format is unusual: {quote}"
        
        return f"Could not find stock quote for {symbol}. API response: {data}"
    
    except requests.exceptions.HTTPError as e:
        return f"HTTP Request Failed: {e}"
    except Exception as e:
        return f"Stock Tool Runtime Error: {str(e)}"


# -------------------------------------------------------
# MODEL WITH TOOL BINDING
# -------------------------------------------------------

api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")

llm_with_tools = ChatOpenAI(
    model="google/gemini-2.0-flash-001",
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=api_key,
).bind_tools([
    ddg_search,
    wiki_tool,
    calculator_tool, 
    stock_tool,
])

# -------------------------------------------------------
# STATE
# -------------------------------------------------------
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# -------------------------------------------------------
# CHAT NODE
# -------------------------------------------------------
def chat_node(state: ChatState):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

# -------------------------------------------------------
# TOOL NODE (FINAL ROBUST VERSION)
# -------------------------------------------------------
def tool_node(state: ChatState):
    last_msg = state["messages"][-1]

    if not hasattr(last_msg, "tool_calls") or not last_msg.tool_calls:
        return {"messages": [AIMessage(content="No tool call detected")]}

    outputs = []

    # Map tool names (as used by the LLM) to the actual tool objects
    tool_map = {
        "duckduckgo_search": ddg_search,
        "wikipedia": wiki_tool, # CONFIRMED NAME
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
                out = f"Unknown tool: {name}. Mapped tools are: {list(tool_map.keys())}"
            
            # Handling for search runnables (single string input expected by .invoke/.run)
            elif name in ["duckduckgo_search", "wikipedia"]:
                # FIX: Ensure we cleanly get the string. LangChain tools usually 
                # use 'query' or 'input' as the key for single inputs.
                query = args.get('query') or args.get('input') 
                
                if query is None and args:
                    # Fallback to the first value if key isn't 'query' or 'input'
                    query = list(args.values())[0]
                
                if query is None:
                     raise ValueError("Query input missing for search tool.")
                
                # Use .invoke() with the raw string
                out = tool_to_call.invoke(query)
            
            # Handling for custom @tool functions (StructuredTool objects)
            elif name in ["calculator_tool", "stock_tool"]:
                # Use .invoke() and pass the entire args dictionary
                out = tool_to_call.invoke(args) 
            
            else:
                 out = f"Tool '{name}' not mapped correctly."

        except Exception as e:
            tb = traceback.format_exc()
            print(f"[TOOL ERROR] {name} raised {type(e).__name__}: {e}\n{tb}")
            out = f"Tool '{name}' failed: {type(e).__name__}: {e}"

        # Ensure output is a string
        if not isinstance(out, str):
            out = str(out)

        # Append the ToolMessage
        outputs.append(
            ToolMessage(
                content=out,
                tool_call_id=tool_call_id,
                name=name
            )
        )

    return {"messages": outputs}


# -------------------------------------------------------
# GRAPH SETUP
# -------------------------------------------------------
graph = StateGraph(ChatState)

graph.add_node("chat", chat_node)
graph.add_node("tool", tool_node)

graph.add_edge(START, "chat")

graph.add_conditional_edges(
    "chat",
    lambda state:
        "tool" if hasattr(state["messages"][-1], "tool_calls") and state["messages"][-1].tool_calls else END,
    {
        "tool": "tool",
        END: END
    }
)

graph.add_edge("tool", "chat")

# -------------------------------------------------------
# MEMORY
# -------------------------------------------------------
conn = sqlite3.connect("chat_memory.db", check_same_thread=False)
if SqliteSaver is not None:
    try:
        memory = SqliteSaver(conn)
    except Exception as e:
        print(f"Warning: SqliteSaver initialization failed: {e}")
        memory = None
else:
    print("Warning: langgraph.checkpoint.sqlite.SqliteSaver not available. Running without persistent memory.")
    memory = None

if memory is not None:
    chatbot = graph.compile(checkpointer=memory)
else:
    chatbot = graph.compile()

# -------------------------------------------------------
# RUN
# -------------------------------------------------------
if __name__ == "__main__":
    print("AI Chatbot started! (type 'exit' to quit)\n")

    thread_id = "session_49" 
    print(f"Using thread_id: {thread_id}\n")

    while True:
        user_input = input("You: ")

        if user_input.lower() in ["exit", "quit"]:
            print("Chat ended.")
            break
        
        response = chatbot.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config={"configurable": {"thread_id": thread_id}}
        )

        ai_message = next((m.content for m in reversed(response["messages"]) if isinstance(m, AIMessage)), "No final response received.")
        
        print("AI:", ai_message, "\n")