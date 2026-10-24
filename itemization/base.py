# Basic idea: Define a common itemize(pages) interface for every approach.
# Prefer creating a separate file for each implementation (e.g., heuristic.py
# or llm.py). Subclass Itemizer and implement itemize() using the shared models.
# This is a starting point; nothing is set in stone.

from abc import ABC, abstractmethod

from .models import ItemizationResult, Page


class Itemizer(ABC):
    @abstractmethod
    def itemize(self, pages: list[Page]) -> ItemizationResult:
        pass
