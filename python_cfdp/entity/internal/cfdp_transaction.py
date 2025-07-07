from __future__ import annotations

from datetime import datetime

from ..cfdp_transaction_state import CfdpTransactionState


class CfdpTransaction:
    """Placeholder for a CFDP transaction."""

    def __init__(self, transaction_id: int, entity: 'CfdpEntity'):
        self.transaction_id = transaction_id
        self.entity = entity
        self.state = CfdpTransactionState.RUNNING
        self.start_time = datetime.utcnow()

    def cancel(self):
        self.state = CfdpTransactionState.CANCELLED

    def dispose(self):
        self.state = CfdpTransactionState.COMPLETED
