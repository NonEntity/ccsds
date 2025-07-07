from abc import ABC, abstractmethod

from python_cfdp.common.cfdp_runtime_exception import CfdpRuntimeException

from .i_cfdp_file_segmenter import ICfdpFileSegmenter


class ICfdpSegmentationStrategy(ABC):
    """Strategy for segmenting a file into CFDP file segments."""

    @abstractmethod
    def support(self, mib: 'Mib', filestore: 'IVirtualFilestore', full_path: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def new_segmenter(self, mib: 'Mib', filestore: 'IVirtualFilestore', full_path: str, destination_entity_id: int) -> ICfdpFileSegmenter:
        raise NotImplementedError
