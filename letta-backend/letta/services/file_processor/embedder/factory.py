from typing import Optional

from letta.schemas.embedding_config import EmbeddingConfig
from letta.services.file_processor.embedder.anthropic_embedder import AnthropicEmbedder
from letta.services.file_processor.embedder.base_embedder import BaseEmbedder
from letta.settings import model_settings


def create_embedder(embedding_config: Optional[EmbeddingConfig] = None) -> BaseEmbedder:
    """Create an embedder instance based on configuration."""
    if not embedding_config:
        embedding_config = EmbeddingConfig(
            embedding_model="claude-3-opus-20240229",
            embedding_endpoint_type="anthropic",
            embedding_endpoint="https://api.anthropic.com/v1/messages",
            api_key=model_settings.anthropic_api_key,
            embedding_chunk_size=8000,
            embedding_overlap=200,
            batch_size=10
        )
    return AnthropicEmbedder(embedding_config=embedding_config)