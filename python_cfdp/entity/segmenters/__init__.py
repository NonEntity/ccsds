"""Python implementation of CFDP file segmentation utilities."""

from .file_segment import FileSegment
from .i_cfdp_file_segmenter import ICfdpFileSegmenter
from .i_cfdp_segmentation_strategy import ICfdpSegmentationStrategy
from .impl.fixed_size_segmenter import FixedSizeSegmenter
from .impl.fixed_size_segmentation_strategy import FixedSizeSegmentationStrategy

__all__ = [
    "FileSegment",
    "ICfdpFileSegmenter",
    "ICfdpSegmentationStrategy",
    "FixedSizeSegmenter",
    "FixedSizeSegmentationStrategy",
]
