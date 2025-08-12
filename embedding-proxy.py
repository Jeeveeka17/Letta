#!/usr/bin/env python3
"""
OpenAI-compatible embedding proxy for Weaviate's transformer service.
This makes the transformer service compatible with Letta's OpenAI client.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import asyncio
from typing import List, Union
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Embedding Proxy", version="1.0.0")

# Transformer service endpoint
TRANSFORMER_ENDPOINT = "http://t2v-transformers:8080/vectors/"

class EmbeddingRequest(BaseModel):
    input: Union[str, List[str]]
    model: str = "sentence-transformers/all-MiniLM-L6-v2"

class EmbeddingData(BaseModel):
    object: str = "embedding"
    embedding: List[float]
    index: int

class EmbeddingResponse(BaseModel):
    object: str = "list"
    data: List[EmbeddingData]
    model: str
    usage: dict

@app.post("/embeddings")
async def create_embeddings(request: EmbeddingRequest):
    """OpenAI-compatible embedding endpoint"""
    try:
        # Handle both string and list inputs
        texts = [request.input] if isinstance(request.input, str) else request.input
        
        embeddings = []
        async with httpx.AsyncClient() as client:
            for i, text in enumerate(texts):
                # Call transformer service
                response = await client.post(
                    TRANSFORMER_ENDPOINT,
                    json={"text": text},
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    logger.error(f"Transformer service error: {response.status_code} - {response.text}")
                    raise HTTPException(status_code=500, detail="Embedding service error")
                
                result = response.json()
                embeddings.append(EmbeddingData(
                    embedding=result["vector"],
                    index=i
                ))
        
        return EmbeddingResponse(
            data=embeddings,
            model=request.model,
            usage={
                "prompt_tokens": sum(len(text.split()) for text in texts),
                "total_tokens": sum(len(text.split()) for text in texts)
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing embedding request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "embedding-proxy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
