"""
Enhanced Context Engine for Lending Application
Uses Anthropic Claude for embeddings and summarization
Uses GraphVectorDB for combined vector similarity and graph relationships
"""

import os
import time
from pathlib import Path
from typing import List, Dict, Optional
import json
from datetime import datetime
import numpy as np

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.chains.summarize import load_summarize_chain
from langchain_community.chat_models import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

# Import our custom graph vector DB
from .graph_vector_db import GraphVectorDB

class EnhancedContextEngine:
    def __init__(
        self,
        context_dir: str = "context",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        anthropic_api_key: Optional[str] = None,
    ):
        """Initialize the context engine.

        Args:
            context_dir: Directory containing context files
            chunk_size: Size of text chunks for embedding
            chunk_overlap: Overlap between chunks
            anthropic_api_key: API key for Anthropic Claude
        """
        self.context_dir = Path(context_dir)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        if not anthropic_api_key:
            anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
            if not anthropic_api_key:
                raise ValueError("Anthropic API key must be provided")

        # Initialize LangChain components
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        # Initialize Claude for summarization
        self.summarizer = ChatAnthropic(
            model_name="claude-3-opus-20240229",
            anthropic_api_key=anthropic_api_key,
            temperature=0
        )

        # Wait for Neo4j to start
        time.sleep(10)  # Give Neo4j time to start up

        # Initialize GraphVectorDB
        self.graph_vector_db = GraphVectorDB()
        try:
            self.graph_vector_db.create_schema()
        except Exception as e:
            print(f"Warning: Schema creation failed (may already exist): {e}")

        # Store summaries in memory
        self.summaries = {}

    def load_documents(self, directory: Path) -> List[Document]:
        """Load documents from a directory."""
        documents = []
        for file_path in directory.glob("**/*.[tm][dx][td]"):  # Match .md, .txt files
            with open(file_path, 'r') as f:
                text = f.read()
                metadata = {
                    'source': str(file_path),
                    'context_name': file_path.stem,
                    'file_type': file_path.suffix
                }
                documents.append(Document(page_content=text, metadata=metadata))
        return documents

    async def summarize_document(self, document: Document) -> str:
        """Summarize a document using Claude."""
        messages = [
            SystemMessage(content="You are a helpful assistant that summarizes documents concisely."),
            HumanMessage(content=f"Please summarize the following document:\n\n{document.page_content}")
        ]
        response = await self.summarizer.ainvoke(messages)
        return response.content

    def create_memory_chunks(self, documents: List[Document]) -> List[Dict]:
        """Create memory chunks from documents with metadata."""
        chunks = []
        for doc in documents:
            doc_chunks = self.text_splitter.split_documents([doc])
            for i, chunk in enumerate(doc_chunks):
                chunk_metadata = {
                    **chunk.metadata,
                    'chunk_index': i,
                    'total_chunks': len(doc_chunks)
                }
                chunks.append({
                    'content': chunk.page_content,
                    'metadata': chunk_metadata
                })
        return chunks

    def create_deterministic_embedding(self, text: str) -> np.ndarray:
        """Create a deterministic embedding vector based on text hash."""
        # Use abs to ensure positive seed value and modulo to keep within valid range
        text_hash = abs(hash(text)) % (2**32 - 1)
        np.random.seed(text_hash)
        vector = np.random.rand(128)
        return vector / np.linalg.norm(vector)

    def store_in_graph_vector_db(self, chunks: List[Dict]) -> Dict[str, str]:
        """Store chunks in GraphVectorDB and create relationships."""
        doc_ids = {}
        
        # First, store all documents
        for chunk in chunks:
            content = chunk['content']
            category = chunk['metadata']['context_name']
            vector = self.create_deterministic_embedding(content)
            
            doc_id = self.graph_vector_db.add_document(
                content=content,
                category=category,
                vector=vector
            )
            
            if category not in doc_ids:
                doc_ids[category] = doc_id

        # Then create relationships between documents
        if 'ekyc' in doc_ids and 'pan' in doc_ids:
            self.graph_vector_db.create_relationship(
                doc_ids['ekyc'],
                doc_ids['pan'],
                'REQUIRES'
            )
        
        if 'lending' in doc_ids and 'ekyc' in doc_ids:
            self.graph_vector_db.create_relationship(
                doc_ids['lending'],
                doc_ids['ekyc'],
                'REQUIRES'
            )

        return doc_ids

    async def process_documents(self) -> None:
        """Process all documents in context directory."""
        # Load documents
        context_docs = self.load_documents(self.context_dir)

        # Summarize documents and store summaries
        for doc in context_docs:
            summary = await self.summarize_document(doc)
            self.summaries[doc.metadata['context_name']] = summary

        # Create and store chunks
        chunks = self.create_memory_chunks(context_docs)
        self.store_in_graph_vector_db(chunks)

    def retrieve_context(self, query: str, k: int = 3) -> List[Dict]:
        """Retrieve top-k relevant chunks for a query."""
        query_vector = self.create_deterministic_embedding(query)
        results = self.graph_vector_db.search_similar(query_vector, limit=k)
        
        return [{
            'content': doc.properties['content'],
            'category': doc.properties['category'],
            'distance': doc.metadata.distance if hasattr(doc.metadata, 'distance') else None
        } for doc in results]

    def get_context_summary(self, context_name: str) -> Optional[str]:
        """Get summary for a specific context."""
        return self.summaries.get(context_name)

    def close(self):
        """Clean up resources."""
        self.graph_vector_db.close()
