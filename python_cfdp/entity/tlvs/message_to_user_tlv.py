from dataclasses import dataclass
from typing import Optional


@dataclass
class MessageToUserTLV:
    """Simple container for user messages."""

    data: Optional[bytes]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"MessageToUserTLV{{data={self.data}}}"
