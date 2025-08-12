"""
Schema definitions for the context engine
"""
from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class ContentType(str, Enum):
    CAPABILITY = "capability"
    PROMPT = "prompt"
    CODE = "code"
    DOCUMENTATION = "documentation"

class DomainType(str, Enum):
    LENDING = "lending"
    PAYMENT = "payment"
    COMPLIANCE = "compliance"
    SECURITY = "security"

class LayerType(str, Enum):
    SERVICE = "service"
    CONTROLLER = "controller"
    ENTITY = "entity"
    REPOSITORY = "repository"
    UTILITY = "utility"

class ChunkMetadata(BaseModel):
    """Metadata for a memory chunk"""
    content_type: ContentType
    domain: DomainType
    layer: Optional[LayerType]
    capability_name: str
    file_path: str
    language: Optional[str]
    chunk_index: int
    total_chunks: int
    tags: List[str] = Field(default_factory=list)
    summary: Optional[str]

class MemoryChunk(BaseModel):
    """A chunk of memory with content and metadata"""
    content: str
    metadata: ChunkMetadata
    embedding: Optional[List[float]]

class MCPFormat(BaseModel):
    """Model Context Protocol format"""
    type: str = "context"
    content: str
    code_snippet: Optional[str]
    metadata: ChunkMetadata
    related_chunks: List[str] = Field(default_factory=list)
    version: str = "1.0"