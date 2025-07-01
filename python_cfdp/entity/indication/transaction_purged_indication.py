from dataclasses import dataclass, field
from typing import List

from .i_cfdp_indication import ICfdpIndication


@dataclass
class TransactionPurgedIndication(ICfdpIndication):
    """Indication that transactions have been purged from the entity."""

    transaction_ids: List[int] = field(default_factory=list)
