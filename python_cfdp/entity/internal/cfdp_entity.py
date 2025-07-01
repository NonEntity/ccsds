from typing import Dict, List, Optional, Set

from ..i_cfdp_entity import ICfdpEntity
from ..i_cfdp_entity_subscriber import ICfdpEntitySubscriber
from ..segmenters import ICfdpSegmentationStrategy, FixedSizeSegmentationStrategy
from ..request import ICfdpRequest


class CfdpEntity(ICfdpEntity):
    """Greatly simplified placeholder implementation of a CFDP entity."""

    def __init__(self, mib, filestore, transaction_id_generator=None, layers=None):
        self.mib = mib
        self.filestore = filestore
        self.transaction_id_generator = transaction_id_generator
        self.layers = layers or []
        self.subscribers: List[ICfdpEntitySubscriber] = []
        self.transactions: Dict[int, 'CfdpTransaction'] = {}
        self.segmentation_strategies: List[ICfdpSegmentationStrategy] = [FixedSizeSegmentationStrategy()]

    def add_segmentation_strategy(self, strategy: ICfdpSegmentationStrategy) -> None:
        self.segmentation_strategies.insert(0, strategy)

    def get_transaction_ids(self) -> Set[int]:
        return set(self.transactions.keys())

    def request(self, request: ICfdpRequest) -> None:
        # Real implementation would enqueue the request
        pass

    def purge_completed_transactions(self) -> None:
        self.transactions.clear()

    def dispose(self) -> None:
        self.transactions.clear()
        self.subscribers.clear()

    def get_ut_layers(self) -> List[str]:
        return [l.get_name() for l in self.layers]
