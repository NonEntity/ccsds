from dataclasses import dataclass
from typing import Optional

from .i_cfdp_transaction_indication import ICfdpTransactionIndication
from ..condition_code import ConditionCode
from ..cfdp_transaction_status import CfdpTransactionStatus


@dataclass
class FaultIndication(ICfdpTransactionIndication):
    """Indication emitted when a fault occurred and was ignored."""

    condition_code: ConditionCode
    progress: int
    status_report: Optional[CfdpTransactionStatus] = None

    def __str__(self) -> str:  # pragma: no cover - simple
        return (
            f"FaultIndication{{transaction_id={self.transaction_id}, "
            f"condition_code={self.condition_code}, progress={self.progress}, "
            f"status_report={self.status_report}}}"
        )
