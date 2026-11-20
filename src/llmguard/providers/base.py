"""The interface every LLM provider implements.

A Protocol is Python's way of saying "anything with these methods counts".
Guard depends on this, not on Gemini, so tests can swap in a fake.
"""

from typing import Protocol


class Provider(Protocol):
    def generate(self, prompt: str, system: str | None = None) -> str: ...
