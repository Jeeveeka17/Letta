from typing import Optional

from letta.interfaces.anthropic_streaming_interface import AnthropicStreamingInterface
from letta.interfaces.base_interface import BaseInterface
from letta.schemas.llm_config import LLMConfig


def create_default_interface(llm_config: Optional[LLMConfig] = None) -> BaseInterface:
    """Create the default streaming interface."""
    if not llm_config:
        llm_config = LLMConfig(
            model="claude-3-opus-20240229",
            model_endpoint_type="anthropic",
            model_endpoint="https://api.anthropic.com/v1/messages",
            context_window=100000,
            max_tokens=4096,
            put_inner_thoughts_in_kwargs=True
        )
    return AnthropicStreamingInterface(llm_config=llm_config)


