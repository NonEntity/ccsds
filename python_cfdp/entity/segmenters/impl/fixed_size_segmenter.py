from typing import Optional

from ..file_segment import FileSegment
from ..i_cfdp_file_segmenter import ICfdpFileSegmenter


class FixedSizeSegmenter(ICfdpFileSegmenter):
    """Simple segmenter that yields fixed-size chunks from a file-like object."""

    def __init__(self, filestore, full_path: str, maximum_file_segment_length: int):
        self.filestore = filestore
        self.full_path = full_path
        self.max_length = maximum_file_segment_length
        self._stream: Optional[any] = None
        self._offset = 0

    def next_segment(self) -> FileSegment:
        if self._stream is None:
            self._stream = self.filestore.read_file(self.full_path)
            self._offset = 0
        data = self._stream.read(self.max_length)
        if not data:
            return FileSegment.eof_segment()
        offset = self._offset
        self._offset += len(data)
        return FileSegment(offset, data)

    def close(self) -> None:
        if self._stream:
            self._stream.close()
            self._stream = None
