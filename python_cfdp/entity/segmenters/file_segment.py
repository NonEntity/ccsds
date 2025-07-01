from dataclasses import dataclass
from typing import Optional


@dataclass
class FileSegment:
    """A file segment used during CFDP file transmission."""

    offset: int
    data: Optional[bytes]
    metadata: Optional[bytes] = None
    record_continuation_state: int = 0
    eof: bool = False

    @staticmethod
    def eof_segment() -> 'FileSegment':
        return FileSegment(-1, None, None, 0, True)
