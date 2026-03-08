"""
Base collector interface for AI Daily data sources.
"""

from abc import ABC, abstractmethod
from typing import List
from app.schemas import SourceItem


class BaseCollector(ABC):
    """All AI Daily collectors implement this interface."""

    name: str = "base"
    source_type: str = "media"
    lang: str = "zh"

    @abstractmethod
    async def collect(self) -> List[SourceItem]:
        """Fetch and return standardized SourceItems from this data source."""
        ...
