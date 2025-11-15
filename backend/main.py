# Save this content into a new file named 'main.py'

from fastapi import FastAPI
# ... (all other necessary imports)

# Initialize the FastAPI app
app = FastAPI(title="LangGraph Chatbot API")

# ... (the rest of the LangGraph and endpoint logic)

# If you include this, Uvicorn will run when you execute the script directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)