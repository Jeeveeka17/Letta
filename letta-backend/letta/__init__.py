import os
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("letta")
except PackageNotFoundError:
    # Fallback for development installations
    __version__ = "0.9.1"

if os.environ.get("LETTA_VERSION"):
    __version__ = os.environ["LETTA_VERSION"]

# import clients
from .client.client import RESTClient

# Import sqlite_functions early to ensure event handlers are registered
from .orm import sqlite_functions

# # imports for easier access
from .schemas.agent import AgentState
from .schemas.block import Block
from .schemas.embedding_config import EmbeddingConfig
from .schemas.enums import JobStatus
from .schemas.file import FileMetadata
from .schemas.job import Job
from .schemas.letta_message import LettaMessage
from .schemas.letta_stop_reason import LettaStopReason
from .schemas.llm_config import LLMConfig
from .schemas.memory import ArchivalMemorySummary, BasicBlockMemory, ChatMemory, Memory, RecallMemorySummary
from .schemas.message import Message
from .schemas.organization import Organization
from .schemas.passage import Passage
from .schemas.source import Source
from .schemas.tool import Tool
from .schemas.usage import LettaUsageStatistics
from .schemas.user import User
