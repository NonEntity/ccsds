from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .cfdp_transaction_state import CfdpTransactionState
from .cfdp_transmission_mode import CfdpTransmissionMode
from .condition_code import ConditionCode


@dataclass
class CfdpTransactionStatus:
    """Status of a CFDP transaction."""

    time: datetime
    managing_entity: 'ICfdpEntity'
    transaction_id: int
    source_entity_id: int
    destination_entity_id: int
    is_destination: bool
    last_condition_code: ConditionCode
    last_fault_entity: Optional[int]
    cfdp_transaction_state: CfdpTransactionState
    progress: int
    total_file_size: int
    transmission_mode: CfdpTransmissionMode
    last_received_pdu_time: Optional[datetime]
    last_sent_pdu_time: Optional[datetime]
    real_progress: int
