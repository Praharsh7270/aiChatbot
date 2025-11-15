from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage # Import specific message types
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv, dotenv_values

# Load environment variables from a .env file if present (development)
load_dotenv()
env_values = dotenv_values()
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
# You no longer need: from openai import OpenAI 

# --- 1. DEFINE THE LLM RUNNABLE ---
# Use ChatOpenAI, which is a LangChain Runnable
# It points to OpenRouter and uses the correct DeepSeek model
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
    temperature=0
)

conn = sqlite3.connect(database='chatbot2.db', check_same_thread=False)
# Checkpointer
checkpointer = SqliteSaver(conn=conn)

# --- 2. DEFINE STATE AND NODE ---
class ChatState(TypedDict):
        
     # LangGraph uses a list of BaseMessage objects for chat history
        messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):
    # This node now uses the .invoke() method on the LangChain LLM
    response = llm.invoke(state['messages'])
    # The response is an AIMessage object, which is a BaseMessage and correct for the state
    return {'messages': [response]}

# --- 3. COMPILE GRAPH ---


graph = StateGraph(ChatState) # Use the correct state name (ChatState)
graph.add_node('chat_node', chat_node) # Use the correct node name (chat_node)
graph.add_edge(START, 'chat_node')
graph.add_edge('chat_node', END)

chatbot = graph.compile()

# --- 4. RUN THE CHATBOT ---
# Initial message to start the conversation
initial_message = HumanMessage(content="What is the meaning of life?")

# Run the graph
# The .invoke method takes a dictionary matching the state keys
thread_id = "my-first-chat-session"
response = chatbot.invoke(
    {"messages": [initial_message]},
    config={"configurable": {"thread_id": thread_id}}
)


# Print the final response content
# The response is the final state, so we get the last message from the 'messages' list
print(response['messages'][-1].content)