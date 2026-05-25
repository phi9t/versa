from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        ...

    @abstractmethod
    async def generate_json(self, prompt: str, schema: type[T]) -> T:
        ...
