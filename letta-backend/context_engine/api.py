from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import uvicorn
from .enhanced_context_engine import EnhancedContextEngine

app = FastAPI(title="Letta Context Engine API")

# Initialize context engine
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    with open(".env") as f:
        for line in f:
            if line.startswith("ANTHROPIC_API_KEY="):
                api_key = line.strip().split("=")[1].strip('"').strip("'")
                break
if not api_key:
    raise ValueError("Could not find ANTHROPIC_API_KEY in environment or .env file")

os.environ["ANTHROPIC_API_KEY"] = api_key  # Set it in environment for langchain
context_engine = EnhancedContextEngine(anthropic_api_key=api_key)

class Query(BaseModel):
    text: str
    k: Optional[int] = 3

class ContextResponse(BaseModel):
    content: str
    category: str
    distance: Optional[float] = None

@app.post("/query", response_model=List[ContextResponse])
async def query_context(query: Query):
    """Query the context engine for relevant information."""
    try:
        results = context_engine.retrieve_context(query.text, k=query.k)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/summary/{context_name}")
async def get_summary(context_name: str):
    """Get summary for a specific context."""
    summary = context_engine.get_context_summary(context_name)
    if not summary:
        raise HTTPException(status_code=404, detail=f"No summary found for {context_name}")
    return {"context": context_name, "summary": summary}

@app.post("/process")
async def process_documents():
    """Process all documents in the context directory."""
    try:
        await context_engine.process_documents()
        return {"status": "success", "message": "Documents processed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """Initialize the context engine on startup."""
    try:
        await context_engine.process_documents()
    except Exception as e:
        print(f"Error initializing context engine: {e}")

@app.on_event("shutdown")
def shutdown_event():
    """Clean up resources on shutdown."""
    context_engine.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
