"""Python implementation of CFDP file segmentation utilities."""

from .file_segment import (
    FileSegment,
    RCS_NO_START_NO_END,
    RCS_START_NO_END,
    RCS_NO_START_END,
    RCS_START_END,
    RCS_NOT_PRESENT,
)
from .i_cfdp_file_segmenter import ICfdpFileSegmenter
from .i_cfdp_segmentation_strategy import ICfdpSegmentationStrategy
from .impl.fixed_size_segmenter import FixedSizeSegmenter
from .impl.fixed_size_segmentation_strategy import FixedSizeSegmentationStrategy

__all__ = [
    "FileSegment",
    "RCS_NO_START_NO_END",
    "RCS_START_NO_END",
    "RCS_NO_START_END",
    "RCS_START_END",
    "RCS_NOT_PRESENT",
    "ICfdpFileSegmenter",
    "ICfdpSegmentationStrategy",
    "FixedSizeSegmenter",
    "FixedSizeSegmentationStrategy",
]
