from abc import ABC, abstractmethod
from typing import Iterable

from .file_segment import FileSegment


class ICfdpFileSegmenter(ABC):
    """Iterator-like interface returning file segments."""

    @abstractmethod
    def next_segment(self) -> FileSegment:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        pass
