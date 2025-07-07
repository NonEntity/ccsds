from __future__ import annotations

from .condition_code import ConditionCode
from python_cfdp.common import CfdpException


class FaultDeclaredException(CfdpException):
    """Raised when a CFDP fault condition is detected."""

    def __init__(self, transaction_id: int, action: str, condition_code: ConditionCode, generating_entity_id: int):
        super().__init__(
            f"Transaction {transaction_id}: fault with code 0x{condition_code:02X} "
            f"detected from entity {generating_entity_id}, action {action}"
        )
        self.action = action
        self.condition_code = condition_code
        self.generating_entity_id = generating_entity_id
        self.transaction_id = transaction_id
