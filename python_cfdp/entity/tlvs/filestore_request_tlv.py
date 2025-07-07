from dataclasses import dataclass
from typing import Optional

from .action_code import ActionCode


@dataclass
class FilestoreRequestTLV:
    """Description of a filestore operation."""

    action_code: ActionCode
    first_file_name: Optional[str]
    second_file_name: Optional[str] = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        return (
            f"FilestoreRequestTLV{{action_code={self.action_code}, "
            f"first_file_name='{self.first_file_name}', "
            f"second_file_name='{self.second_file_name}'}}"
        )
