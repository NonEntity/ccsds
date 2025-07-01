from abc import ABC, abstractmethod
from typing import Collection, List, Set

from .i_transaction_id_generator import ITransactionIdGenerator
from .segmenters.i_cfdp_segmentation_strategy import ICfdpSegmentationStrategy


class ICfdpEntity(ABC):
    """CFDP entity interface."""

    @abstractmethod
    def add_segmentation_strategy(self, strategy: ICfdpSegmentationStrategy) -> None:
        pass

    @abstractmethod
    def get_transaction_ids(self) -> Set[int]:
        pass

    @abstractmethod
    def request(self, request: 'ICfdpRequest') -> None:
        pass

    @abstractmethod
    def purge_completed_transactions(self) -> None:
        pass

    @abstractmethod
    def dispose(self) -> None:
        pass

    @abstractmethod
    def get_ut_layers(self) -> List[str]:
        pass
