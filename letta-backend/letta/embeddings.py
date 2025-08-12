import numpy as np
from typing import List, Union, Optional
import anthropic

class EmbeddingModel:
    def __init__(self, model: str = "claude-3-opus-20240229"):
        self.model = model

    def get_text_embedding(self, text: str) -> List[float]:
        """
        Get embeddings for text using deterministic random vectors.
        This is a placeholder until Claude has a dedicated embeddings API.
        
        Args:
            text: The text to get embeddings for
            
        Returns:
            A 128-dimensional vector embedding
        """
        # Use deterministic random vectors based on text hash
        text_hash = hash(text)
        np.random.seed(text_hash)
        vector = np.random.rand(128)
        # Normalize the vector
        vector = vector / np.linalg.norm(vector)
        return vector.tolist()

def embedding_model(config: Optional[dict] = None) -> EmbeddingModel:
    """
    Get an embedding model instance based on config.
    This function is used by the connectors.
    
    Args:
        config: Optional configuration for the embedding model
        
    Returns:
        An EmbeddingModel instance
    """
    model = "claude-3-opus-20240229"
    if config and hasattr(config, 'model'):
        model = config.model
    return EmbeddingModel(model=model)

def get_embedding(text: str, model: str = "claude-3-opus-20240229") -> np.ndarray:
    """
    Get embeddings for text.
    
    Args:
        text: The text to get embeddings for
        model: The model to use
        
    Returns:
        A 128-dimensional vector embedding
    """
    embed_model = EmbeddingModel(model=model)
    return np.array(embed_model.get_text_embedding(text))

def get_embeddings(texts: List[str], model: str = "claude-3-opus-20240229") -> List[np.ndarray]:
    """
    Get embeddings for multiple texts.
    
    Args:
        texts: List of texts to get embeddings for
        model: The model to use
        
    Returns:
        List of embeddings vectors
    """
    embed_model = EmbeddingModel(model=model)
    return [np.array(embed_model.get_text_embedding(text)) for text in texts]
