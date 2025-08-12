"""
Context Engine for Lending Application
Uses Anthropic Claude for embeddings and summarization
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
import json
from datetime import datetime

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.chains.summarize import load_summarize_chain
from langchain.chat_models import ChatAnthropic
from langchain.embeddings import BedrockEmbeddings
from langchain.vectorstores.pgvector import PGVector
from letta_client import CreateBlock, Letta, MessageCreate

class ContextEngine:
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
        
        # Initialize Claude for summarization and embeddings
        self.summarizer = ChatAnthropic(
            anthropic_api_key=anthropic_api_key,
            model="claude-3-opus-20240229"
        )
        
        # Initialize embeddings using Claude
        self.embeddings = BedrockEmbeddings(
            model_id="anthropic.claude-v2",
            credentials_profile_name="default",
            region_name="us-west-2"
        )
        
        # Initialize Letta client
        self.letta_client = Letta(base_url="http://localhost:8283")
        
        # Initialize PGVector store
        self.connection_string = f"postgresql+psycopg2://letta:lettapass@vector_db:5432/vector_store"
        self.vector_store = None

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
        chain = load_summarize_chain(
            llm=self.summarizer,
            chain_type="map_reduce",
            verbose=True
        )
        summary = await chain.arun([document])
        return summary

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

    def store_in_letta(self, chunks: List[Dict]) -> None:
        """Store chunks in Letta memory."""
        for chunk in chunks:
            # Create a memory block for each chunk
            block = self.letta_client.blocks.create(
                label=f"context_{chunk['metadata']['context_name']}_{chunk['metadata']['chunk_index']}",
                value=json.dumps({
                    'content': chunk['content'],
                    'metadata': chunk['metadata']
                }),
                read_only=True
            )

    def build_vector_store(self, chunks: List[Dict]) -> None:
        """Build vector store from chunks using PostgreSQL."""
        texts = [chunk['content'] for chunk in chunks]
        metadatas = [chunk['metadata'] for chunk in chunks]
        
        # Create vector store in PostgreSQL
        self.vector_store = PGVector.from_texts(
            texts=texts,
            embedding=self.embeddings,
            metadatas=metadatas,
            connection_string=self.connection_string,
            collection_name="letta_context"
        )

    async def process_documents(self) -> None:
        """Process all documents in context directory."""
        # Load documents
        context_docs = self.load_documents(self.context_dir)

        # Summarize documents
        for doc in context_docs:
            summary = await self.summarize_document(doc)
            doc.metadata['summary'] = summary

        # Create and store chunks
        chunks = self.create_memory_chunks(context_docs)
        self.store_in_letta(chunks)
        self.build_vector_store(chunks)

    def retrieve_context(self, query: str, k: int = 3) -> List[Dict]:
        """Retrieve top-k relevant chunks for a query."""
        if not self.vector_store:
            raise ValueError("Vector store not built. Run process_documents first.")
        
        results = self.vector_store.similarity_search_with_score(query, k=k)
        return [{
            'content': doc.page_content,
            'metadata': doc.metadata,
            'score': score
        } for doc, score in results]

    def get_context_summary(self, context_name: str) -> Optional[str]:
        """Get summary for a specific context."""
        blocks = self.letta_client.blocks.list(label=f"context_{context_name}_0")
        if not blocks:
            return None
        
        chunk_data = json.loads(blocks[0].value)
        return chunk_data['metadata'].get('summary')

class MCPWrapper:
    """Optional MCP wrapper for standardizing context format."""
    
    @staticmethod
    def wrap_context(context: Dict) -> Dict:
        """Wrap context in MCP format."""
        return {
            "type": "context",
            "content": context['content'],
            "metadata": {
                "context": context['metadata']['context_name'],
                "source": context['metadata']['source'],
                "summary": context['metadata'].get('summary', ''),
                "chunk_info": {
                    "index": context['metadata']['chunk_index'],
                    "total": context['metadata']['total_chunks']
                }
            }
        }

    @staticmethod
    def wrap_query(query: str) -> Dict:
        """Wrap query in MCP format."""
        return {
            "type": "query",
            "content": query,
            "metadata": {
                "timestamp": str(datetime.now())
            }
        }
