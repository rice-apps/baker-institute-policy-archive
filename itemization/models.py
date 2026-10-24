# Basic idea: Define shared page and result dataclasses, including boundary
# scores and reasons, so all itemizers use the same input and output format.
# This is a starting point; nothing is set in stone.

from dataclasses import dataclass

@dataclass
class Page:
    pass

@dataclass
class ItemizationResult:
    pass
