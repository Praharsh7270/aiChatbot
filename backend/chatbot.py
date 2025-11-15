from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage 
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv, dotenv_values
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

load_dotenv()
env_values = dotenv_values()

api_key = env_values.get("OPENROUTER_API_KEY") or env_values.get("OPENAI_API_KEY")
if not api_key:
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

checkpointer = SqliteSaver(conn=conn)

class ChatState(TypedDict):
        messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):
    response = llm.invoke(state['messages'])
    return {'messages': [response]}


graph = StateGraph(ChatState) # Use the correct state name (ChatState)
graph.add_node('chat_node', chat_node) # Use the correct node name (chat_node)
graph.add_edge(START, 'chat_node')
graph.add_edge('chat_node', END)

chatbot = graph.compile()
initial_message = HumanMessage(content="What is the meaning of life?")
thread_id = "my-first-chat-session"
response = chatbot.invoke(
    {"messages": [initial_message]},
    config={"configurable": {"thread_id": thread_id}}
)
print(response['messages'][-1].content)