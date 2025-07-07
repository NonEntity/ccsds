from dataclasses import dataclass
from typing import Optional

# Record continuation state constants mirroring the Java implementation
RCS_NO_START_NO_END = 0x00
RCS_START_NO_END = 0x01
RCS_NO_START_END = 0x02
RCS_START_END = 0x03
RCS_NOT_PRESENT = 0xFF


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


__all__ = [
    "FileSegment",
    "RCS_NO_START_NO_END",
    "RCS_START_NO_END",
    "RCS_NO_START_END",
    "RCS_START_END",
    "RCS_NOT_PRESENT",
]
