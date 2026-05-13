"""
Memory Backend · Abstract Base

All backends implement this interface.
The MemoryEngine auto-selects between SQLite and Hindsight.
"""
from abc import ABC, abstractmethod
from typing import Optional


class MemoryBackend(ABC):
    """Pluggable memory backend interface.

    Three operations (Hindsight-compatible protocol):
    - retain: store something
    - recall: search for relevant memories
    - reflect: synthesize across memories
    """

    @abstractmethod
    def retain(self, content: str, context: str = "",
               tags: list = None, memory_type: str = "event") -> bool:
        """Store something into memory."""
        ...

    @abstractmethod
    def recall(self, query: str, limit: int = 10) -> dict:
        """Search across all memory tiers.
        Returns: {"facts": [], "events": [], "narratives": [], "sessions": []}
        """
        ...

    @abstractmethod
    def reflect(self, question: str) -> dict:
        """Synthesize across memories to answer a question.
        Returns: {"question": str, "correction_patterns": [], ...}
        """
        ...

    @abstractmethod
    def stats(self) -> dict:
        """Memory backend statistics."""
        ...

    def close(self):
        """Cleanup (optional)."""
        pass

    @property
    def name(self) -> str:
        return self.__class__.__name__.replace("Backend", "").lower()
