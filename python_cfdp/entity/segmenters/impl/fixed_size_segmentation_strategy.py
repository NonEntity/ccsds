from ..i_cfdp_segmentation_strategy import ICfdpSegmentationStrategy
from ..i_cfdp_file_segmenter import ICfdpFileSegmenter
from .fixed_size_segmenter import FixedSizeSegmenter


class FixedSizeSegmentationStrategy(ICfdpSegmentationStrategy):
    """Segmentation strategy producing fixed size segments for any file."""

    def support(self, mib, filestore, full_path: str) -> bool:  # noqa: D401 - doc inherited
        return True

    def new_segmenter(self, mib, filestore, full_path: str, destination_entity_id: int) -> ICfdpFileSegmenter:  # noqa: D401
        return FixedSizeSegmenter(filestore, full_path, mib.get_remote_entity_by_id(destination_entity_id).get_maximum_file_segment_length())
