from __future__ import annotations

from typing import Any

from pr_agent.memory_providers.mem0_provider import Mem0MemoryProvider

_memory_provider: Any = None

# TODO: Add other memory providers here.
def get_memory_provider():
    global _memory_provider
    if _memory_provider is None:
        _memory_provider = Mem0MemoryProvider()
    return _memory_provider
